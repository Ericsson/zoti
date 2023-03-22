/*
 * Copyright (C) Ericsson AB, 2019
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 * 
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 * 
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <inttypes.h>
#include <poll.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
#include <time.h>
#include "dfl_evt.h"

typedef struct dfl_evt_port {
  dfl_evt_socktype_t socktype;
  uint16_t port;
  int fd;
  dfl_evt_reader reader;
  dfl_evt_reader reader_to_install;
} dfl_evt_port_t;

#define PORTS_MAX 20
static dfl_evt_port_t ports[PORTS_MAX];
static struct pollfd active_polls[PORTS_MAX];
static size_t high_mark = 0;
static size_t last_poll_idx = 0;

static int64_t next_time_trig = 0;
static dfl_evt_timer_action timer_action;

#define NSECS_IN_SEC 1000000000LL
#define NSEC_50 50000


int dfl_evt_add_timer(int64_t timeout_nsecs, dfl_evt_timer_action evt_action)
{
  if (timeout_nsecs >= 0) {
    struct timespec now_ts;
    int res = clock_gettime(CLOCK_REALTIME, &now_ts);
    if (res == 0) {
      int64_t now = ((int64_t)now_ts.tv_sec) * NSECS_IN_SEC + now_ts.tv_nsec;
      next_time_trig = now + timeout_nsecs;
      timer_action = evt_action;
      return 0;
    }
    printf("Error: clock_gettime() returned %d\n", res);
  }
  next_time_trig = 0;
  timer_action = 0;
  return 0;
}


static int find_free_slot()
{
  /* Search for a free slot in the ports and polls tables. */
  size_t idx = 0;
  for (; idx < high_mark; ++idx) {
    if (ports[idx].port == 0) {
      break;
    }
  }
  if (idx >= high_mark) {
    ++high_mark;
    if (high_mark >= PORTS_MAX) {
      return -1;
    }
  }

  return idx;
}


static int find_slot_by_sock(int sock)
{
  size_t idx = 0;
  for (; idx < high_mark; ++idx) {
    if (ports[idx].fd == sock) {
      return idx;
    }
  }

  return -1;
}


static void set_slot(int idx, dfl_evt_socktype_t socktype,
                     uint16_t port, int sock,
                     dfl_evt_reader evt_reader,
                     dfl_evt_reader reader_to_install)
{
  /* Now register the socket in our ports table. */
  ports[idx] = (dfl_evt_port_t){
    .socktype = socktype,
    .port = port,
    .fd = sock,
    .reader = evt_reader,
    .reader_to_install = reader_to_install
  };

  /* And set up corresponding entry in the polling table. */
  active_polls[idx] = (struct pollfd){
    .fd = sock,
    .events = POLLIN
  };
}


static void accept_connection(int acc_sock)
{
  int acc_idx = find_slot_by_sock(acc_sock);
  if (acc_idx < 0) {
    printf("accept_connection(), cannot find slot for sock %d\n",
           acc_sock);
    return;
  }

  int new_sock = accept(acc_sock, 0, 0);
  if (new_sock < 0) {
    printf("accept_connection() failed, errno=%d\n", errno);
    return;
  }

  int idx = find_free_slot();
  if (idx < 0) {
    printf("accept_connection(), port list is full\n");
    return;
  }

  set_slot(idx, ports[acc_idx].socktype, ports[acc_idx].port,
           new_sock, ports[acc_idx].reader_to_install, 0);
}


int dfl_evt_add_port(dfl_evt_socktype_t socktype,
                     uint16_t port, dfl_evt_reader evt_reader)
{
  int idx = find_free_slot();
  if (idx < 0) {
    printf("dfl_evt_add_port(), port list is full\n");
    return -1;
  }

  /* Create a socket for the port and bind it. */
  int socktype_ll;
  const char *socktype_str;
  dfl_evt_reader action_fn, reader_to_install;
  switch (socktype) {
  case dfl_evt_socktype_udp:
    socktype_ll = SOCK_DGRAM;
    socktype_str = "UDP";
    action_fn = evt_reader;
    reader_to_install = 0;
    break;
  case dfl_evt_socktype_tcp:
    socktype_ll = SOCK_STREAM;
    socktype_str = "TCP";
    action_fn = accept_connection;
    reader_to_install = evt_reader;
    break;
  default:
    printf("Unsupported socktype: %d\n", socktype);
    return -4;
  }
  printf("Creating socket of type: %s\n", socktype_str);
  int sock = socket(AF_INET, socktype_ll, 0);
  printf("  sock=%d\n", sock);
  if (sock < 0) {
    return -2;
  }
  const int reuse = 1;
  if (setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse)) < 0) {
    printf("  Error: (%d) %s\n", errno, strerror(errno));
    return -6;
  }
  struct sockaddr_in saddr = {
    .sin_family = AF_INET,
    .sin_addr.s_addr = htonl(INADDR_ANY),
    .sin_port = htons(port),
  };
  printf("Binding socket, sin_port=%d\n", saddr.sin_port);
  if (bind(sock, (struct sockaddr *)&saddr, sizeof(saddr)) < 0) {
    printf("  Error: (%d) %s\n", errno, strerror(errno));
    return -3;
  }

  /* For TCP sockets we need also to listen for connections. */
  if (socktype == dfl_evt_socktype_tcp) {
    if (listen(sock, 5) != 0) {
      printf("Failed to set socket to listen: errno=%d\n", errno);
      return -5;
    }
  }

  set_slot(idx, socktype, port, sock, action_fn, reader_to_install);

  return 0;
}


int dfl_evt_wait_n_eval(void)
{
  int res = 0;
  int64_t timeout = INT64_MAX;
  struct timespec timeout_ts;
  struct timespec *timeout_p = 0;
  int64_t now = 0;
  struct timespec now_ts = {0};
  do {
    if (next_time_trig > 0) {
      res = clock_gettime(CLOCK_REALTIME, &now_ts);
      if (res != 0) {
        printf("Error: clock_gettime() returned %d\n", res);
        next_time_trig = 0;
        timeout = -1;
      } else {
        now = ((int64_t)now_ts.tv_sec) * NSECS_IN_SEC + now_ts.tv_nsec;
        timeout = (next_time_trig - now);
        if (timeout < 0) {
          timeout = 0;
        }
      }
    } else {
      timeout = -1;
    }
    #ifdef DFL_DEBUG_PRINT
    printf("Calling poll, timeout=%"PRId64"\n", timeout);
    #endif
    if (timeout < 0) {
      timeout_p = 0;
    } else {
      timeout_ts.tv_sec = timeout / NSECS_IN_SEC;
      timeout_ts.tv_nsec = timeout % NSECS_IN_SEC;
      timeout_p = &timeout_ts;
    }
    res = ppoll(active_polls, high_mark, timeout_p, 0);
    #ifdef DFL_DEBUG_PRINT
    printf("  res=%d\n", res);
    #endif
    if (res < 0) {
      if (errno == EINTR) {
        errno = 0;
        continue;
      }
      printf("  ppoll() exited with errno=%d\n", errno);
      return res;
    }
    if (res == 0) {
      res = clock_gettime(CLOCK_REALTIME, &now_ts);
      if (res != 0) {
        printf("Error: clock_gettime() returned %d\n", res);
        next_time_trig = 0;
        timeout = -1;
      } else {
        now = ((int64_t)now_ts.tv_sec) * NSECS_IN_SEC + now_ts.tv_nsec + NSEC_50;
        if (now >= next_time_trig && next_time_trig > 0) {
          next_time_trig = 0;
          timer_action(now);
          return 0;
        }
      }
    }
    if (res > 0 && high_mark > 0) {
      size_t idx = last_poll_idx + 1;
      while (idx != last_poll_idx) {
        if (idx >= high_mark) {
          idx = 0;
        }
        last_poll_idx = idx;
        short revents = active_polls[idx].revents;
        if (revents & (POLLERR | POLLHUP | POLLNVAL)) {
          printf("  ppoll: revents=%x\n", revents);
          return -10;
        }
        if ((revents & POLLIN) != 0) {
          ports[idx].reader(ports[idx].fd);
          return 0;
        }
        ++idx;
      }
    }
  } while (1);
}


int dfl_evt_cfg_outport(dfl_evt_socktype_t socktype, int *sock_p,
                        const char *dst_addr, uint16_t dst_port)
{
  int socktype_ll;
  int protocol;
  const char *socktype_str;
  switch (socktype) {
  case dfl_evt_socktype_udp:
    socktype_ll = SOCK_DGRAM;
    protocol = IPPROTO_UDP;
    socktype_str = "UDP";
    break;
  case dfl_evt_socktype_tcp:
    socktype_ll = SOCK_STREAM;
    protocol = IPPROTO_TCP;
    socktype_str = "TCP";
    break;
  default:
    printf("Unsupported socktype: %d\n", socktype);
    return -4;
  }

  /* Obtain address matching host/port */
  struct addrinfo hints = (struct addrinfo){
    .ai_family = AF_INET,    /* IPv4 */
    .ai_socktype = socktype_ll,
    .ai_flags = 0,
    .ai_protocol = protocol
  };
  struct addrinfo *adr_info;
  char ip_port_str[100];
  int sock = -1;
  int res;

  sprintf(ip_port_str, "%" PRIu16, dst_port);
  printf("Calling getaddrinfo: socktype='%s', dst_addr='%s', "
         "ip_port='%s'\n", socktype_str, dst_addr, ip_port_str);
  res = getaddrinfo(dst_addr, ip_port_str, &hints, &adr_info);
  if (res != 0) {
    printf("getaddrinfo: %s\n", gai_strerror(res));
    return -1;
  }

  /* Create a socket for BearerPort. */
  printf("Creating socket\n");
  sock = socket(adr_info->ai_family,
                adr_info->ai_socktype,
                adr_info->ai_protocol);
  printf("  sock=%d\n", sock);
  if (sock < 0) {
    printf("Failed to create socket\n");
    return -2;
  }

  if (connect(sock, adr_info->ai_addr, adr_info->ai_addrlen) != 0) {
    printf("Failed to connect socket\n");
    close(sock);
    return -3;
  }

  freeaddrinfo(adr_info);
  *sock_p = sock;
  return 0;
}

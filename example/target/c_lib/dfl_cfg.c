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

#include <stdio.h>


#include <errno.h>
#include <string.h>
#include <stdlib.h>
#include <stdbool.h>
#include <stdint.h>
#include <inttypes.h>
#include <poll.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include "dfl_cfg.h"


#define FLAG_STOP_ARG_PARSE "--"
#define FLAG_CFG_PORT "--dfl-cfg-port"

/* struct json_tokener {}; */
/* struct json_object {}; */
/* static struct json_tokener *json_tok = 0; */

static dfl_cfg_in_port_handler_t in_port_handler = 0;
static dfl_cfg_out_port_handler_t out_port_handler = 0;
static dfl_cfg_timer_handler_t timer_handler = 0;
static dfl_cfg_atom_handler_t atom_handler = 0;

int dfl_cfg_set_handlers(dfl_cfg_in_port_handler_t in_port_hdlr,
                         dfl_cfg_out_port_handler_t out_port_hdlr,
                         dfl_cfg_timer_handler_t timer_hdlr,
                         dfl_cfg_atom_handler_t atom_hdlr)
{
  in_port_handler = in_port_hdlr;
  out_port_handler = out_port_hdlr;
  timer_handler = timer_hdlr;
  atom_handler = atom_hdlr;
  return 0;
}


int dfl_cfg_parse_args(int argc, char *argv[], uint16_t *cfg_port)
{
  int i;
  size_t cfg_flag_len = strlen(FLAG_CFG_PORT);
  bool port_found = false;
  for (i = 0; i < argc; ++i) {
    if (strcmp(argv[i], FLAG_STOP_ARG_PARSE) == 0) {
      break;
    }
    if (strncmp(argv[i], FLAG_CFG_PORT, cfg_flag_len) == 0) {
      const char *val_str = 0;
      if (argv[i][cfg_flag_len] == '=') {
        val_str = &argv[i][cfg_flag_len+1];
      }
      else {
        ++i;
        if (i >= argc) {
          val_str = ""; /* Caught as invalid port later. */
        }
        else {
          val_str = argv[i];
        }
      }
      printf("Arg %s = \"%s\"\n", FLAG_CFG_PORT, val_str);

      char *end;
      errno = 0;
      long int arg_val = strtol(val_str, &end, 0);
      if (end == val_str) {
        fprintf(stderr, "Arg error: Invalid port \"%s\"\n", val_str);
        return -2;
      }
      if (errno == ERANGE || arg_val <= 0 || arg_val > UINT16_MAX) {
        fprintf(stderr, "Arg error: Port (%s) out of range\n", val_str);
        errno = 0;
        return -3;
      }
      *cfg_port = arg_val;
      port_found = true;
      break;
    }
  }
  if (!port_found) {
    fprintf(stderr, "Arg error: Mandatory flag %s missing\n", FLAG_CFG_PORT);
    return -1;
  }
  return 0;
}


static int parse_next_element(const char **parse_point, char *elem_buf, int buf_size)
{
  const char *line = *parse_point;
  const int max_size = (buf_size-1) > 0 ? (buf_size-1) : 0;
  /* int res = -1; */

  printf("parse next: '%s'\n", line);

  int line_idx = 0;
  int tgt_idx = 0;
  for (; tgt_idx < max_size && line[line_idx] != ',' &&
         line[line_idx] != '\n' && line[line_idx] != '\0';
       line_idx++, tgt_idx++) {
    elem_buf[tgt_idx] = line[line_idx];
  }
  elem_buf[tgt_idx] = '\0';

  char end_char = line[line_idx];
  if (end_char == ',') {
    *parse_point = line + line_idx + 1;
    return 1;
  }
  if (end_char == '\n') {
    *parse_point = line + line_idx + 1;
    return 0;
  }
  if (end_char == '\0') {
    *parse_point = 0;
    return 0;
  }
  return -91;
}


static int process_in_port(const char **parse_point)
{
  int parse_res = 0;
  int res;
  char name[100];
  char host[100];
  char nr_buf[20];
  int32_t ip_port;
  char *parse_end;

  if (! in_port_handler) {
    printf("process_in_port(): No in-port handler present.\n");
    return 0;
  }

  parse_res = parse_next_element(parse_point, name, sizeof(name));
  if (parse_res < 0 || name[0] == '\0') {
    printf("process_in_port(): port name not found in csv line, status=%d.\n", parse_res);
    return parse_res;
  }

  parse_res = parse_next_element(parse_point, host, sizeof(host));
  if (parse_res < 0) {
    /* An empty host is okay, it should be treated as localhost. Actually, at the
       moment we do not use the host element at all for in-ports, but might in
       the future. */
    printf("process_in_port(): host address not found in csv line, status=%d.\n", parse_res);
    return parse_res;
  }

  parse_res = parse_next_element(parse_point, nr_buf, sizeof(nr_buf));
  if (parse_res < 0 || nr_buf[0] == '\0') {
    printf("process_in_port(): IP port number not found in csv line, status=%d.\n", parse_res);
    return parse_res;
  }
  ip_port = strtol(nr_buf, &parse_end, 0);
  if (nr_buf[0] == '\0' || *parse_end != '\0') {
    printf("process_in_port(): IP port number is not a valid number.\n");
    return -41;
  }

  res = in_port_handler(name, ip_port);
  if (res < 0) {
    printf("process_in_port(): In-port configuration failed, "
           "res=%d, name=\"%s\", ip_port=%"PRId32"\n", res, name, ip_port);
    return -42;
  }

  return 0;
}


static int process_out_port(const char **parse_point)
{
  int parse_res = 0;
  int res;
  char name[100];
  char host[100];
  char nr_buf[20];
  int32_t ip_port;
  char *parse_end;

  if (! out_port_handler) {
    printf("process_out_port(): No out-port handler present.\n");
    return 0;
  }

  parse_res = parse_next_element(parse_point, name, sizeof(name));
  if (parse_res < 0 || name[0] == '\0') {
    printf("process_out_port(): port name not found in csv line, "
           "status=%d.\n", parse_res);
    return parse_res;
  }

  parse_res = parse_next_element(parse_point, host, sizeof(host));
  if (parse_res < 0) {
    printf("process_out_port(): host address not found in csv line, "
           "status=%d.\n", parse_res);
    return parse_res;
  }
  if (host[0] == '\0') {
    /* An empty host is okay, it is treated as localhost. */
    strcpy(host, "localhost");
  }

  parse_res = parse_next_element(parse_point, nr_buf, sizeof(nr_buf));
  if (parse_res < 0 || nr_buf[0] == '\0') {
    printf("process_out_port(): IP port number not found in csv line, "
           "status=%d.\n", parse_res);
    return parse_res;
  }
  ip_port = strtol(nr_buf, &parse_end, 0);
  if (nr_buf[0] == '\0' || *parse_end != '\0') {
    printf("process_out_port(): IP port number is not a valid number.\n");
    return -51;
  }

  res = out_port_handler(name, host, ip_port);
  if (res < 0) {
    printf("process_out_port(): Out-port configuration failed, "
           "res=%d, name=\"%s\", name=\"%s\", ip_port=%"PRId32"\n",
           res, name, host, ip_port);
    return -52;
  }

  return 0;
}


static int process_timer(const char **parse_point)
{
  printf("process_timer(): NYI, handler=%p\n", timer_handler);
  return 0;
}


typedef struct {
  char *name;
  uint32_t id_nr;
} atom_entry_t;


static void clean_atom_list(atom_entry_t *atoms, int len)
{
  for (int i=0; i < len; i++) {
    free(atoms[i].name);
  }
}

static int process_atoms(const char **parse_point)
{
  int parse_res = 1;
  int res;
  char name[100];
  char nr_buf[20];
  int32_t id_nr;
  char *parse_end;

  const int MAX_ATOMS = 100;
  atom_entry_t atoms[MAX_ATOMS];
  int atoms_len = 0;

  if (! atom_handler) {
    printf("process_atom(): No atom handler present.\n");
    return 0;
  }

  if (*parse_point == 0) {
    /* Previous parsing has come to the end of the line. We still need to send
       things to the node process so that it can come out of the first config
       stage. */
    parse_res = 0;
  }
  while (parse_res > 0 && atoms_len < MAX_ATOMS) {
    parse_res = parse_next_element(parse_point, name, sizeof(name));
    if (parse_res < 0 || name[0] == '\0') {
      printf("process_atoms(): missing atom name in csv line, "
             "status=%d.\n", parse_res);
      clean_atom_list(atoms, atoms_len);
      return parse_res;
    }

    parse_res = parse_next_element(parse_point, nr_buf, sizeof(nr_buf));
    if (parse_res < 0 || nr_buf[0] == '\0') {
      printf("process_atoms(): missing atom ID in csv line, "
             "status=%d.\n", parse_res);
      clean_atom_list(atoms, atoms_len);
      return parse_res;
    }
    id_nr = strtol(nr_buf, &parse_end, 0);
    if (nr_buf[0] == '\0' || *parse_end != '\0') {
      printf("process_atoms(): atom ID is not a valid number.\n");
      clean_atom_list(atoms, atoms_len);
      return -71;
    }
    if (id_nr < 0) {
      printf("process_atoms(): invalid atom ID: %"PRIi32".\n", id_nr);
      clean_atom_list(atoms, atoms_len);
      return -72;
    }

    atoms[atoms_len].name = strdup(name);
    atoms[atoms_len].id_nr = id_nr;
    atoms_len++;
  }
  if (parse_res > 0 && atoms_len >= MAX_ATOMS) {
    printf("process_atoms(): too many atoms.\n");
    clean_atom_list(atoms, atoms_len);
    return -73;
  }

  for (int i = 0; i < atoms_len; ++i) {
    res = atom_handler(atoms_len, atoms[i].name, atoms[i].id_nr);
    if (res < 0) {
      printf("process_atom(): Atom configuration failed, "
             "res=%d, name=\"%s\", id_nr=%"PRIu32"\n",
             res, atoms[i].name, atoms[i].id_nr);
      clean_atom_list(atoms, atoms_len);
      return -74;
    }
  }
  clean_atom_list(atoms, atoms_len);

  /* A final call to the atom handler checks that all atoms have been
     configured. */
  res = atom_handler(atoms_len, 0, 0);
  if (res < 0) {
    printf("process_atom(): Atom configuration check failed, res=%d\n", res);
    return -75;
  }

  return 0;
}


static int process_csv_line(const char **parse_point)
{
  int parse_res = 0;
  char cfg_kind[20];

  parse_res = parse_next_element(parse_point, cfg_kind, sizeof(cfg_kind));
  if (parse_res < 0) {
    printf("process_csv_line(): config kind not found in csv line, status=%d.\n", parse_res);
    return -31;
  }

  if (strcmp(cfg_kind, "in-port") == 0) {
    process_in_port(parse_point);
    return parse_res;
  }
  if (strcmp(cfg_kind, "out-port") == 0) {
    process_out_port(parse_point);
    return parse_res;
  }
  if (strcmp(cfg_kind, "timer") == 0) {
    process_timer(parse_point);
    return parse_res;
  }
  if (strcmp(cfg_kind, "atoms") == 0) {
    process_atoms(parse_point);
    return parse_res;
  }

  printf("process_csv_line(): Unknown config kind: \"%s\"\n", cfg_kind);
  return -32;
}


void dfl_cfg_read_and_process(int sock)
{
  int process_res = 0;
  char buf[1000];
  char line[1001]; /* size is 1 more than for buf to be on the safe side */
  size_t recv_cnt = 0;
  while (0 == (recv_cnt = recvfrom(sock, buf, sizeof(buf), 0, 0, 0)));
  if (recv_cnt < 0) {
    printf("dfl_cfg_read_n_process(): recvfrom failed, status=%ld\n", recv_cnt);
    return;
  }

  int buf_idx = 0;
  while (buf_idx < recv_cnt) {
    int tgt_idx = 0;
    for (; buf_idx < recv_cnt && buf[buf_idx] != '\n'; buf_idx++, tgt_idx++) {
      line[tgt_idx] = buf[buf_idx];
    }
    line[tgt_idx] = '\0';

    const char *parse_point = line;
    process_res = process_csv_line(&parse_point);
    if (process_res < 0) {
      return;
    }
  }
}

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

#include <stdint.h>

typedef enum {
  dfl_evt_socktype_none = 0,
  dfl_evt_socktype_udp,
  dfl_evt_socktype_tcp
} dfl_evt_socktype_t;

typedef void (*dfl_evt_timer_action)(int64_t now);
typedef void (*dfl_evt_reader)(int DFL_socket);

extern int dfl_evt_add_timer(int64_t timeout_secs,
                             dfl_evt_timer_action evt_action);
extern int dfl_evt_add_port(dfl_evt_socktype_t socktype,
                            uint16_t port, dfl_evt_reader evt_reader);
extern int dfl_evt_wait_n_eval(void);
extern int dfl_evt_cfg_outport(dfl_evt_socktype_t socktype,
                               int *sock_p, const char *dst_addr,
                               uint16_t dst_port);

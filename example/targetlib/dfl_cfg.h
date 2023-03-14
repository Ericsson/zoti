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

typedef int (*dfl_cfg_in_port_handler_t)(char *name, int32_t ip_port);
typedef int (*dfl_cfg_out_port_handler_t)(char *name,
                                          char *ip_addr, int32_t ip_port);
typedef int (*dfl_cfg_timer_handler_t)(char *name, uint64_t timeout);
typedef int (*dfl_cfg_atom_handler_t)(size_t cnt, char *name, uint32_t id_nr);


extern int dfl_cfg_parse_args(int argc, char *argv[], uint16_t *cfg_port);

extern void dfl_cfg_read_and_process(int sock);

extern int dfl_cfg_set_handlers(dfl_cfg_in_port_handler_t in_port_hdlr,
                                dfl_cfg_out_port_handler_t out_port_hdlr,
                                dfl_cfg_timer_handler_t timer_hdlr,
                                dfl_cfg_atom_handler_t atom_hdlr);
/* Note, above function args timer_hdlr and atom_hdlr are currently ignored. */

/*
 * Copyright (C) Ericsson AB, 2020
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
#ifndef DFL_CORE_H
#define DFL_CORE_H

#include <stdint.h>

typedef uint32_t DFL_atom_t;

enum {
  DFL_ATOM_INVALID_BIT = 0x80000000,
  DFL_ATOM_MASK = 0x7FFFFFFF
};

static inline bool DFL_atom_is_valid(DFL_atom_t atom) {
  return (atom & DFL_ATOM_INVALID_BIT) == 0;
}

typedef struct DFL_atom_entry {
  const char *name;
  DFL_atom_t id_nr;
} DFL_atom_entry_t;

#endif

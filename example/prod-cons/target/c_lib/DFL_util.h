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
#ifndef DFL_UTIL_H
#define DFL_UTIL_H

#include <stdint.h>

static inline uint16_t DFL_swap_uint16(uint16_t v)
{
  return ((v >> 8) & 0xff) | ((v << 8) & 0xff00);
}

static inline int16_t DFL_swap_int16(uint16_t v)
{
  return (int16_t) DFL_swap_uint16(v);
}

static inline uint32_t DFL_swap_uint32(uint32_t v)
{
  return ((v >> 24) & 0xff) | ((v >> 8) & 0xff00) | ((v << 8) & 0xff0000)
    | ((v << 24) & 0xff000000);
}

static inline int32_t DFL_swap_int32(uint32_t v)
{
  return (int32_t) DFL_swap_uint32(v);
}

static inline uint64_t DFL_swap_uint64(uint64_t v)
{
  return ((v >> 56) & 0xff) | ((v >> 40) & 0xff00)
    | ((v >> 24) & 0xff0000) | ((v >> 8) & 0xff000000)
    | ((v << 8) & 0xff00000000) | ((v << 24) & 0xff0000000000)
    | ((v << 40) & 0xff000000000000) | ((v << 56) & 0xff00000000000000);
}

static inline int64_t DFL_swap_int64(uint64_t v)
{
  return (int64_t) DFL_swap_uint64(v);
}

#endif

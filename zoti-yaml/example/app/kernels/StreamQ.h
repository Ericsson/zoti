#ifndef STREAMQ_H
#define STREAMQ_H

#include <stdio.h>

#define STREAMQ_BEARERS_MAX 50
#define STREAMQ_BLOCKS_MAX 10000
#define STREAMQ_DATA_MAX 200
typedef struct {
  uint32_t a, b, c;
} data_t;
static data_t StreamQ_stored_data[STREAMQ_BEARERS_MAX][STREAMQ_BLOCKS_MAX][STREAMQ_DATA_MAX];
static int16_t StreamQ_block_start[STREAMQ_BEARERS_MAX] = {-2};
static int16_t StreamQ_block_next[STREAMQ_BEARERS_MAX] = {0};
static uint16_t StreamQ_stored_length[STREAMQ_BEARERS_MAX][STREAMQ_BLOCKS_MAX] = {0};
static uint32_t StreamQ_total_length[STREAMQ_BEARERS_MAX] = {0};
static uint16_t StreamQ_block_cnt[STREAMQ_BEARERS_MAX] = {0};

inline static int16_t StreamQ_alloc_block(Common__StreamId_t id)
{
  int16_t blk_nr = StreamQ_block_next[id];
  int16_t blk_start = StreamQ_block_start[id];
  if (blk_nr == blk_start)
    return -1;
  if (blk_nr+1 >= STREAMQ_BLOCKS_MAX)
    StreamQ_block_next[id] = 0;
  else
    StreamQ_block_next[id]++;
  if (blk_start < 0)
    StreamQ_block_start[id] = blk_nr;
  return blk_nr;
}

inline static int16_t StreamQ_pop_block(Common__StreamId_t id)
{
  int16_t blk_nr = StreamQ_block_start[id];
  if (blk_nr >= 0) {
    int16_t blk_start = blk_nr + 1;
    if (blk_start >= STREAMQ_BLOCKS_MAX) {
      blk_start = 0;
    }
    if (blk_start == StreamQ_block_next[id]) {
      StreamQ_block_next[id] = 0;
      StreamQ_block_start[id] = -1;
    } else {
      StreamQ_block_start[id] = blk_start;
    }
  }
  return blk_nr;
}

#endif

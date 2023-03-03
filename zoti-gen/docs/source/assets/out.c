void mulacc(in1, in2, acc, &out) {
  // vvv mulacc
  out = acc + in1 * in2;
  // ^^^ mulacc
};

int main(void) {
  int input[10];
  int output[10];
  int COEF[4] = {1, 2, 2, 1};
  // vvv main
  while (1) {

    // vvv ReadArray

    {
      int __io_it;
      for (__io_it = 0; __io_it < 10; __io_it++) {
        scanf("%d", &input[__io_it]);
      }
    }
    //
    // ^^^ ReadArray

    int _it;
    int _range;
    // vvv mav_1

    for (_it = 0; _it < min(input); _it++) {
      _range = min(input) - _it;
      int _it0;
      int _acc;
      // vvv fred_1

      for (_it0 = 0; _it0 < min(_range, COEF); _it0++) {
        mulacc((input + _it)[_it0], COEF[_it0], _acc, _acc)
      }
      output[_it] = _acc;
      //
      // ^^^ fred_1
    }
    //
    // ^^^ mav_1

    // vvv PrintArray

    {
      int __io_it;
      for (__io_it = 0; __io_it < 10; __io_it++) {
        printf("%d", output[__io_it]);
      }
    }
    //
    // ^^^ PrintArray
  }
  // ^^^ main
}

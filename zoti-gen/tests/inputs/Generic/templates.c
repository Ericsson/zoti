// Template: ReadArray.C
{int __io_it;
  for (__io_it = 0; __io_it < {{ param.size }}; __io_it++){
    scanf({{ param.format }}, &{{ label.arg.name }}[__io_it]);
  }
}
// End: ReadArray.C


// Template: PrintArray.C
{int __io_it;
  for (__io_it = 0; __io_it < {{ param.size }}; __io_it++){
    printf({{ param.format }}, {{ label.arg.name }}[__io_it]);
  }
}
// End: PrintArray.C


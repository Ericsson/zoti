// Template: ReadArray.C
{int __io_it;
  for (__io_it = 0; __io_it < {{port.arg.type.size}}; __io_it++){
    scanf({{ param.format }}, &{{ port.arg.name }}[__io_it]);
  }
}
// End: ReadArray.C


// Template: PrintArray.C
{int __io_it;
  for (__io_it = 0; __io_it < {{port.arg.type.size}}; __io_it++){
    printf({{ param.format }}, {{ port.arg.name }}[__io_it]);
  }
}
// End: PrintArray.C


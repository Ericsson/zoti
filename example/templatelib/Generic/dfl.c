// Template: Main.C
uint16_t cfg_port;
int res = dfl_cfg_parse_args(argc, argv, &cfg_port);
if (res == 0)
  dfl_cfg_set_handlers(0, 0, 0, {{ param.CFG.atom }});
if (res == 0)
  res = dfl_evt_add_port(dfl_evt_socktype_udp, cfg_port, dfl_cfg_read_and_process);
if (res == 0)
  {{ placeholder["INIT_stage1"] }}

while (res == 0) {
  res = dfl_evt_wait_n_eval();
#if defined(DFL_DEBUG_PRINT) && DFL_DEBUG_PRINT >= 5
  printf("cfg loop: res=%d\\n", res);
#endif
  if ({{ label.atom_table_inited.name }}) break;
  if (res > 0) res = 0;
 }

if (res == 0) {
  dfl_cfg_set_handlers({{ param.CFG.inport }},
		       {{ param.CFG.outport }},
		       0,
		       {{ param.CFG.atom }});
  {{ placeholder["INIT_stage2"] }}
 }

while (res == 0) {
  res = dfl_evt_wait_n_eval();
#if defined(DFL_DEBUG_PRINT) && DFL_DEBUG_PRINT >= 5
  printf("main loop: res=%d\\n", res);
#endif
  if (res > 0) res = 0;
 }

if (res != 0) {
  printf("Event loop for Proc-1-src-flat exited with res=%d\n", res);
 }
return (res == 0 ? 0 : 1);
// End: Main.C


// Template: CFG_inport.C
int res = 0;

{% for port in param.iports %}
if (strcmp(name, "{{ port.name }}") == 0) {
  res = dfl_evt_add_port(dfl_evt_socktype_udp, ip_port, {{ port.handler }});
  if (res < 0) printf("ERROR: Inport config failed, port='{{ port.name }}', "
		      "sock_type='dfl_evt_socktype_udp', ip_port=%"PRId32", res=%d\n", ip_port, res);
 }
{% endfor %}

return res;
// End: CFG_inport.C


// Template: CFG_outport.C
int res = 0;

{% for opt in param.oports %}
if (strcmp(name, "{{ opt.name }}") == 0) {
  res = dfl_evt_cfg_outport(dfl_evt_socktype_udp, &{{ label[opt.socket].name }}, ip_addr, ip_port);
    if (res < 0) printf("ERROR: Outport config failed, port='{{ opt.name }}', "
                        "sock_type='dfl_evt_socktype_udp', ip_addr='%s', ip_port=%"PRId32", res=%d\n",
                        ip_addr, ip_port, res);
  }
{% endfor %}

return res;
// End: CFG_outport.C

// Template: CFG_atom.C
{% if param.init_table == true %}
if ({{ label.dyn_table.name }} == 0) {
  {{ label.dyn_table.name }} = malloc(len * sizeof(DFL_atom_entry_t));
 }
if (name == 0) {
  if ({{ label.atom_table_len.name }} != len) {
    printf("ERROR: Mismatch in dyn atom table length, table_len=%zd, len=%zd\n",
	   {{ label.atom_table_len.name }}, len);
    return -33;
  }
  {{ label.dyn_table_inited.name }} = true;
 } else {
  {{ label.dyn_table.name }}[{{ label.atom_table_len.name }}].name = strdup(name);
  {{ label.dyn_table.name }}[{{ label.atom_table_len.name }}].id_nr = id_nr;
  ++{{ label.atom_table_len.name }};
 }

{% endif %}
if (name == 0) {
  for (int i = 0; i < sizeof({{ label.atom_table.name }})/sizeof(0[{{ label.atom_table.name }}]); ++i) {
    if (! DFL_atom_is_valid({{ label.atom_table.name }}[i].id_nr)) {
      printf("ERROR: Atom not configured, name='%s', \n",
	     {{ label.atom_table.name }}[i].name);
      return -31;
    }
  }
  {{ label.atom_table_inited.name }} = true;
  return 0;
 } else {
  for (int i = 0; i < sizeof({{ label.atom_table.name }})/sizeof(0[{{ label.atom_table.name }}]); ++i) {
    if (strcmp({{ label.atom_table.name }}[i].name, name) == 0) {
      {{ label.atom_table.name }}[i].id_nr = id_nr;
      return 0;
    }
  }
  if ({{ label.atom_table_len.name }} > 0) {
    return 0;
  } else {
    printf("ERROR: Atom in config spec not found in atom table, name='%s', "
	   "id_nr=%"PRIu32"\n", name, id_nr);
    return -32;
  }
 }
// End: CFG_atom.C


// Template: UdpReceive.C
size_t {{label.size.name}}_cnt =
  recv({{label.socket.name}},
       &{{label.ram.name}},
       sizeof({{label.ram.name}}),
       0);
/* TODO: Proper error handling needs to be added. */
if ({{label.size.name}} < 0) return;
{{label.size.name}} = (uint16_t){{label.size.name}}_cnt;

if ({{label.size.name}} < {{param.expected_base_size}}) {
#ifdef DFL_DEBUG_PRINT
  printf("Unmarshal type {{ param.expected_type }} failed! Packet size %"PRId32" < header size %"PRId32"\n",
	 (int32_t){{label.size.name}}, (int32_t){{param.expected_base_size}});
#endif
  return;
 }
if ({{label.size.name}} != {{param.expected_size}}) {
#ifdef DFL_DEBUG_PRINT
  printf("Unmarshal type {{ param.expected_type }} failed! Packet size %"PRId32" != expected size %"PRId32"\n",
	 (int32_t){{label.size.name}}, (int32_t){{param.expected_size}});
#endif
  return;
 }
// End: UdpReceive.C

// Template: UdpSend.C
  const size_t {{label.data.name}}_cnt = (sizeof(Tst__LinkData_t) + 100 * (sizeof(Res__Sample_t)));
  if (send({{label.socket.name}},
           {{label.data.name}},
           {{label.data.name}}_cnt,
           0) != {{label.data.name}}_cnt) {
    #ifdef DFL_DEBUG_PRINT
    printf("Send on <<<{{label.socket.name}}>>> failed!\n");
    #endif
  }
// End: UdpSend.C

// Template: Increment.C
++{{label.var.name}};
// End: Increment.C

// Template: TimerReceive.C
{{ setter("timerrecv.seconds", [label.timestamp.name, " / 1000000000LL"] | join("")) }};
{{ setter("timerrecv.nanosecs", ["(uint32_t)(", label.timestamp.name, "% 1000000000LL)"] | join("")) }};

#if defined(DFL_DEBUG_PRINT) && DFL_DEBUG_PRINT >= 3
printf("Timer trigged, now=%"PRIu64" %"PRIu32"\n",
       {{ getter("timerrecv.seconds") }},
       {{ getter("timerrecv.nanosecs") }}
       );
#endif
       
dfl_evt_add_timer({{param.period}}LL, {{param.callback}});
// End: TimerReceive.C


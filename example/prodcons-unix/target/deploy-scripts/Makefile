DEPL 		= python3 deploybins.py
SETUP 		= python3 setupflow.py
FLOOD 		= python3 udpflood.py
DEPLAGENT	= python3 deployagent.py
NAMESERV 	= python3 nameservice.py --debug

DEPL_FLOW = ProdCons-depl

BIN_DIR 	:= $(GEN_DIR)/bin
FLOW_IFLAGS 	:= -I $(GEN_DIR)/tran_out
FLOW_IFLAGS 	+= -I .

download start stop: 
	$(DEPL) -F $(DEPL_FLOW) $(FLOW_IFLAGS) -B $(BIN_DIR) --$@

cfg:
	$(SETUP) -F $(DEPL_FLOW) $(FLOW_IFLAGS) --csv

traffic:
	$(FLOOD) --debug -N trig -c 100000 -s 1

trig:
	$(FLOOD) --debug -N trig -c 1 -s 1

stats:
	$(FLOOD) -N DFL-flush -c 1 -s 1

run:
	$(MAKE) download
	$(MAKE) start
	sleep 1
	$(MAKE) cfg

agents:
	xterm -e '$(DEPLAGENT)' &
	xterm -e '$(NAMESERV)' &

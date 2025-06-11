-- Prepare trigger to accept TSP-triggers
tsplink.initialize()
--- Clear trigger model
trigger.model.load("Empty")
node[2].trigger.model.load("Empty")

-- Set tsp triggeren to send triggers from node 1 (gate) and accept
-- triggers from node 2 (source-drain)
tsplink.line[1].reset()
tsplink.line[1].mode = tsplink.MODE_SYNCHRONOUS_MASTER
tsplink.line[2].mode = tsplink.MODE_SYNCHRONOUS_ACCEPTOR
trigger.tsplinkout[1].stimulus = trigger.EVENT_NOTIFY1
trigger.tsplinkin[2].clear()
trigger.tsplinkin[2].edge = trigger.EDGE_RISING

-- Configure NOTIFY2 to trigger DMM
trigger.digout[1].stimulus = trigger.EVENT_NOTIFY2

node[2].tsplink.line[2].mode = node[2].tsplink.MODE_SYNCHRONOUS_MASTER
node[2].tsplink.line[1].mode = node[2].tsplink.MODE_SYNCHRONOUS_ACCEPTOR
node[2].trigger.tsplinkout[2].stimulus = node[2].trigger.EVENT_NOTIFY2
node[2].trigger.tsplinkin[1].clear()
node[2].trigger.tsplinkin[1].edge = node[2].trigger.EDGE_RISING

-- Build actual trigger model
trigger.model.setblock(1, trigger.BLOCK_NOTIFY, trigger.EVENT_NOTIFY1)
trigger.model.setblock(2, trigger.BLOCK_NOTIFY, trigger.EVENT_NOTIFY2)
trigger.model.setblock(3, trigger.BLOCK_MEASURE_DIGITIZE)

node[2].trigger.model.setblock(1, node[2].trigger.BLOCK_WAIT, node[2].trigger.EVENT_TSPLINK1)
node[2].trigger.model.setblock(2, node[2].trigger.BLOCK_MEASURE_DIGITIZE)

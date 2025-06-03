-- Lua script for taking a single reading on both nodes
node[2].trigger.model.initiate()
trigger.model.initiate()
waitcomplete()
n = node[1].defbuffer1.endindex
m = node[2].defbuffer1.endindex
printbuffer(n, n, node[1].defbuffer1, node[1].defbuffer1.units, node[1].defbuffer1.sourcevalues)
printbuffer(m, m, node[2].defbuffer1, node[2].defbuffer1.units, node[2].defbuffer1.sourcevalues)
print("end " .. n .. " " .. m)

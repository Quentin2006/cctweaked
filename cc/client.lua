local ws = http.websocket("ws://192.168.0.47:3000")
local running = true
if not ws then
	print("Connection Failed")
	return
end

while running do
	-- Wait for a reply (blocks until message or timeout)
	-- server verify user input
	local s_msg = ws.receive()

	print("Received:", s_msg)

	-- Execute received Lua commands
	local ok, err = pcall(load(s_msg))
	if not ok then
		print("Error:", err)
	end
end

-- Close
ws.close()

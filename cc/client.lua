local ws = http.websocket("ws://192.168.0.47:3000")

if not ws then
	print("Connection Failed")
	return
end

-- Send something
print("Enter 'q' to exit and 'h' for help")
while true do
	::continue::
	local c_msg = io.read()

	if c_msg == "q" then
		break
	end

	if c_msg == "h" then
		print("'w': move forward")
		print("'s': move backward")
		print("'a': turn left")
		print("'d': turn right")
		print("'e': move up")
		print("'q': move down")
		goto continue
	end

	-- send the message over
	ws.send(c_msg)

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

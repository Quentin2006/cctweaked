local ws = http.websocket("ws://192.168.0.47:3000")
if not ws then
	print("Connection Failed")
	return
end

while true do
	local s_msg = ws.receive()

	if not s_msg then
		print("Connection lost")
		break
	end

	print("Received:", s_msg)

	local ok, err = pcall(load(s_msg))
	if not ok then
		print("Error:", err)
	end
end

local SERVER_URL = "ws://192.168.0.47:3000"

while true do
	local ws = http.websocket(SERVER_URL)
	if not ws then
		print("Connection failed, retrying in 5s")
		os.sleep(5)
	else
		print("Connected")
		while true do
			local s_msg = ws.receive()
			if not s_msg then
				print("Connection lost, reconnecting...")
				break
			end

			print("Received:", s_msg)

			local ok, err = pcall(load(s_msg))
			if not ok then
				print("Error:", err)
			end
		end
	end
end

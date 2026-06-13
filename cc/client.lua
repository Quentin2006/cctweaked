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

			local ok, data = pcall(textutils.unserializeJSON, s_msg)
			if ok and type(data) == "table" and data.code then
				local fn, compile_err = load(data.code)
				if fn then
					local exec_ok, result = pcall(fn)
					local response = {ok = exec_ok}
					if exec_ok then
						response.result = result
					else
						response.error = tostring(result)
					end
					if data.id then
						response.id = data.id
					end
					ws.send(textutils.serializeJSON(response))
				else
					local response = {ok = false, error = tostring(compile_err)}
					if data.id then
						response.id = data.id
					end
					ws.send(textutils.serializeJSON(response))
				end
			else
				print("Received:", s_msg)
			end
		end
	end
end

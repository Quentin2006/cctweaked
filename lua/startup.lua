local githubUsername = "Quentin2006"
local gistID = "25c7ce5cf7ba79a759436dd427bf8723"
local GIST_DIR = "/gist"

local function downloadFile(url, savePath)
	print("Downloading: " .. savePath)
	if fs.exists(savePath) then
		fs.delete(savePath)
	end
	local response = http.get(url)
	if response then
		local dir = savePath:match("(.*/)")
		if dir and not fs.exists(dir) then
			fs.makeDir(dir)
		end
		local file = fs.open(savePath, "w")
		file.write(response.readAll())
		file.close()
		response.close()
		print("  Saved: " .. savePath)
	else
		print("  Failed: " .. url)
	end
end

local function rmdir(dir)
	if fs.exists(dir) then
		local entries = fs.list(dir)
		for _, entry in ipairs(entries) do
			local path = fs.combine(dir, entry)
			if fs.isDir(path) then
				rmdir(path)
			else
				fs.delete(path)
			end
		end
		fs.delete(dir)
	end
end

local response = http.get("https://api.github.com/gists/" .. gistID)
if not response then
	print("Failed to fetch gist info")
	return
end

local data = textutils.unserializeJSON(response.readAll())
response.close()

local commitSHA = data.history[1].version
local baseURL = "https://gist.githubusercontent.com/" .. githubUsername .. "/" .. gistID .. "/raw/" .. commitSHA

rmdir(GIST_DIR)
fs.makeDir(GIST_DIR)

for filename, _ in pairs(data.files) do
	local lastDot = filename:match(".*()%.")
	local filePath
	if lastDot then
		filePath = filename:sub(1, lastDot - 1):gsub("%.", "/") .. filename:sub(lastDot)
	else
		filePath = filename
	end

	if filename == "startup.lua" then
		fs.delete("/startup.lua")
		downloadFile(baseURL .. "/" .. filename, "/" .. filePath)
	else
		downloadFile(baseURL .. "/" .. filename, fs.combine(GIST_DIR, filePath))
	end
end

print("Synced")
print("Starting client...")
shell.run(GIST_DIR .. "/client.lua")

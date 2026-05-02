require 'webrick'
dir = File.expand_path('..', __FILE__)
server = WEBrick::HTTPServer.new(Port: 3131, DocumentRoot: dir, AccessLog: [], Logger: WEBrick::Log.new('/dev/null'))
trap('INT') { server.stop }
server.start

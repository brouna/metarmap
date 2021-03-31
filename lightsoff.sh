/usr/bin/sudo pkill -F /MetarMap/offpid.pid
/usr/bin/sudo pkill -F /MetarMap/metarpid.pid
/usr/bin/sudo /usr/bin/python3 /MetarMap/pixelsoff.py & echo $! > /MetarMap/offpid.pid


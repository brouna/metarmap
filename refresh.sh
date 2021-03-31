/usr/bin/sudo pkill -F /MetarMap/offpid.pid
/usr/bin/sudo pkill -F /MetarMap/metarpid.pid
sleep 10
/usr/bin/sudo /usr/bin/python3 /MetarMap/metarthread.py 1>>/MetarMap/metarlog.log 2>>/MetarMap/error.log & echo $! > /MetarMap/metarpid.pid


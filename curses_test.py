import curses
import time

screen = curses.initscr()

curses.noecho()
curses.cbreak()
screen.keypad(1)

i = 0
while True: 
    top_pos = 12 
    left_pos = 12 
    screen.addstr(top_pos, left_pos, "i: " + str(i),curses.A_REVERSE)
    screen.refresh()

    i = i+1
    time.sleep(0.1)
    #event = screen.getch() 
    #if event == ord("q"):
        #break


curses.nocbreak();
screen.keypad(0);
curses.echo()
curses.endwin()
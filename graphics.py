import os
import time
import random

def termGraphic():
    '''
        Draw Terminal Graphics
    '''
    BLINK      = '\x1b[5m'
    BG_GREEN   = '\x1b[42;5;36m'
    BOLD       = '\x1b[1m'
    NO_BOLD    = '\x1b[22m'
    ITALIC     = '\x1b[3m'
    NO_ITALIC  = '\x1b[23'
    END        = '\x1b[0m'

    # Bold
    ltb  = '\u259b'
    rtb  = '\u259c'
    lbb  = '\u2599'
    rbb  = '\u259f'
    hrtb = '\u2580'
    hrbb = '\u2584'
    lbar = '\u258c'
    rbar = '\u2590'

    # Semi-bold
    lt  = "┏"
    lb  = "┗"
    rt  = "┓"
    rb  = "┛"
    nl  = "\n"
    hr  = "━"
    vh  = "┃"
    sp  = " "
    csp = BG_GREEN + sp + END # colored space green
    #csp = sp # show outlines

    # Move up, down, right and left n times, clear screen, hide and unhide cursor
    movup      = lambda u: f'\x1b[{u}A' #window_row_size - m
    movdn      = lambda d: f'\x1b[{d}B'
    movr       = lambda r: f'\x1b[{r}C'
    echo       = lambda c: print(c, end="", flush=True)
    movl       = lambda l: f'\x1b[{l}D'
    clrScrn    = lambda: os.system("clear")
    hideCursor = '\x1b[?25l'
    visibleCursor = '\x1b[?25h'

    def initScrn():
        clrScrn()
        echo(hideCursor)

    def drawBorder(w=0, h=0, weight="BOLD"):
        match(weight):
            case "BOLD":
                echo(ltb+hrtb*(w-2)+rtb+nl+(lbar+sp*(w-2)+rbar+nl)*(h-4)+lbb+hrbb*(w-2)+rbb+nl)
            case "SEMI-BOLD":
                echo(BOLD + lt+hr*(w-2)+rt+nl+(vh+sp*(w-2)+vh+nl)*(h-4)+lb+hr*(w-2)+rb+nl + NO_BOLD)
            case "NORMAL":
                echo(lt+hr*(w-2)+rt+nl+(vh+sp*(w-2)+vh+nl)*(h-4)+lb+hr*(w-2)+rb+nl)

    def drawS(w=0, h=0, PAD=""):

        s0 = PAD+lt+(hr*(w-2))+rt+nl
        s1 = PAD+vh+(csp*(w-2))+vh+nl
        s2 = PAD+vh+csp*3+lt+hr*(w-6)+rb+nl
        s3 = PAD+vh+csp*3+vh+nl
        s4 = PAD+vh+csp*3+lb+(hr*(w-6))+rt+nl
        s5 = PAD+vh+csp*(w-2)+vh+nl
        s6 = PAD+lb+hr*(w-6)+rt+csp*3+vh+nl
        s7 = PAD+sp*(w-5)+vh+csp*3+vh+nl
        s8 = PAD+lt+hr*(w-6)+rb+csp*3+vh+nl
        s9 = PAD+vh+csp*(w-2)+vh+nl
        s10= PAD+lb+hr*(w-2)+rb+nl

        echo(s0+s1+s2+s3+s4+s5+s6+s7+s8+s9+s10+movup(11))

    def drawO(w=0, h=0, PAD=""):

        o0 = PAD+lt+hr*(w-2)+rt+nl
        o1 = PAD+vh+csp*(w-2)+vh+nl
        o2 = PAD+vh+csp*4+lt+hr*(w-12)+rt+csp*4+vh+nl
        o3 = (PAD+vh+csp*4+vh+sp*(w-12)+vh+csp*4+vh+nl)*(h-3)
        o4 = PAD+vh+csp*4+lb+hr*(w-12)+rb+csp*4+vh+nl
        o5 = (PAD+vh+csp*(w-2)+vh+nl)*1
        o6 = PAD+lb+hr*(w-2)+rb+nl

        echo(o0+o1+o2+o3+o4+o5+o6+movup(11))

    def drawU(w=0, h=0, PAD=""):

        u0 = PAD+lt+hr*4+rt+sp*(w-12)+lt+hr*4+rt+nl
        u1 = (PAD+vh+csp*4+vh+sp*(w-12)+vh+csp*4+vh+nl)*(h-1)
        u2 = PAD+vh+csp*4+lb+hr*(w-12)+rb+csp*4+vh+nl
        u3 = (PAD+vh+csp*(w-2)+vh+nl)*1
        u4 = PAD+lb+hr*(w-2)+rb+nl

        echo(u0+u1+u2+u3+u4+movup(11))

    def drawL(w=0, h=0, PAD=""):

        l0 = PAD+lt+hr*4+rt+nl
        l1 = (PAD+vh+csp*4+vh+nl)*(h-1)
        l2 = PAD+vh+csp*4+lb+hr*6+rt+nl
        l3 = PAD+vh+csp*(w-4)+vh+nl
        l4 = PAD+lb+hr*(w-4)+rb+nl

        echo(l0+l1+l2+l3+l4+movup(11))

    def slide(txt, /, to=0, step=1, sec=.005, wait=.01, PAD=""):
        '''
            'Slide to Right' transition
        '''
        L = len(txt)
        if col < (to+L):
            return
        time.sleep(wait)
        for i in range(1, to, step):
            echo(PAD+txt)
            time.sleep(sec)
            # clear text annd move a position forward
            echo(movl(L)+sp*L+movl(L-1))
            PAD = "" # Disable padding: pad echoes only once
        echo(txt)


    def echoc(txt, /, effect="", end="", animate=False):
        '''
            Echo to center
        '''
        c = col - len(txt)
        if c < 0:
            return echo(txt)
        if animate:
            animateWrite(txt, effect=movr((c>>1)+1)+effect, end=end)
        else:
            echo(movr((c >> 1)+1)+effect+txt+end)

    def animateWrite(txt, movto=0, effect="", end=""):
        '''
            Animate text echoing
        '''
        echo(effect)
        for char in txt:
            time.sleep(random.choice([0.001, 0.1, 0.05, 0.08, 0.01]))
            echo(char)
            if char == sp:
                time.sleep(0.08)
        echo(end)

    def loader(PAD=""):
        '''
            Loader and status update
        '''
        pass

    def refresh():
        pass

    initScrn()
    col, row = os.get_terminal_size()
    w = 15
    h = 8
    subtitle = "Tracker"
    description	= "Auto Register Members to the Soul Tracker Programme"


    drawBorder(w=col, h=row, weight="SEMI-BOLD")
    echo(movup(row))
    echo(nl)

    center = (col - (w << 2)) >> 1 if (col > (w<<2)) else 0
    center += 1 # the L shape's base is shorter (w-4) rather than (w-2)
    # A cool effect for shapes S O U L, if lines are turning off
    lt, lb, rt, rb, hr, vh = ("", "", "", "", "", "")
    drawS(w=w, h=h, PAD=movr(center))
    drawO(w=w, h=h, PAD=movr(w+center+1))
    drawU(w=w, h=h, PAD=movr(w*2+center+1))
    drawL(w=w, h=h, PAD=movr(w*3+center+1))

    echo(movdn(11))
    slide(subtitle, to=(col-center-len(subtitle)-1), wait=1, PAD=movr(1))
    echo(nl*2)
    echoc(description, effect=ITALIC, end=NO_ITALIC+nl, animate=True)
    echo(nl + movdn(row) + visibleCursor + END)

    '''
        TODO: Fix italics on winterm, auto resize and window limit, loader and percentage progress, miscellenous text
        convert termGraphic to a Class

    '''

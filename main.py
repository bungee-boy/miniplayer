from miniplayer import *

if __name__ == '__main__':
    pg.init()
    player = Miniplayer()

    try:
        while True:
            player.update()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        Log("Main").handle(e)
    finally:
        player.end()
        pg.quit()

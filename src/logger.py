from datetime import datetime


class Logging:
    Last_err = None
    Log = False
    Debug = False

    def __init__(self, name: str):
        self.name = name

    def log(self, msg, cat=None):
        try:
            msg = f"[{datetime.now().strftime('%x %X')}][{cat if cat else 'LOG'}][{self.name}] {msg}."
            print(msg)
            if self.Log:
                with open('miniplayer.log', 'a') as file:
                    file.write(msg + '\n')
        except (Exception, BaseException) as err:
            self.handle(err, save=False)  # Do not save as error with log
        except:
            print('Failed log msg -> unknown')

    def err(self, msg, cat=None, data=None):
        try:
            msg = '[{0}][{1}][{2}] {3}!{4}'.format(datetime.now().strftime('%x %X'), cat if cat else 'ERR', self.name,
                                                   msg, f' ({data})' if data else '')
            print(msg)
            with open('miniplayer_err.log', 'a') as file:
                file.write(msg + '\n')
            if self.Log:
                with open('miniplayer.log', 'a') as file:
                    file.write(msg + '\n')
        except (Exception, BaseException) as err:
            self.handle(err, save=False)  # Do not save as error with log
        except:
            print('Failed log error -> unknown')

    def handle(self, err: Exception or BaseException, save=True, repeat=False, traceback=True):
        if type(err) is KeyboardInterrupt:
            return
        msg = "{0}: {1}".format(str(type(err)).replace("<class '", '').replace("'>", ''), err)
        if not repeat and msg == self.Last_err:
            return
        if self.Debug and traceback:  # Show traceback if debug is on
            import traceback
            traceback.print_exc()
        print(msg)
        self.Last_err = msg
        if save:
            try:
                if self.Debug or self.Log:
                    with open('miniplayer_err.log', 'a') as file:
                        file.write(msg + '\n')
            except:
                print('Failed to log handled error -> unknown')

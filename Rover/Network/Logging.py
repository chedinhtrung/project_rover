class Logger:
    callback = None

    def log(message:str):
        """
        string: string to log
        """
        print(message)
        # TODO: implement the callback to log into the UI

    def set_callback(function):
        Logger.callback = function

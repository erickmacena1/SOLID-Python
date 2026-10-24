class User():
    def __init__(self, username, email):
        self._username = username
        self._email = email

    @staticmethod
    def members():
        return ['user1','user2','user3']
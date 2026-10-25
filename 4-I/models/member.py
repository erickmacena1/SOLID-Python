from .user import User

class Member(User):
    def __init__(self, username, email):
        super().__init__(username, email)

    @staticmethod
    def members():
        return ['user1','user2','user3']
    
    def work(self):
        return "Coding..."

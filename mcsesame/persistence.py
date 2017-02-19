
import config

from sqlalchemy import Column, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import SingletonThreadPool


Base = declarative_base()


class User(Base):

    __tablename__ = 'user'

    login = Column(String(64), primary_key=True)
    passwd = Column(String(64), nullable=False)
    mcuser = Column(String(64), nullable=False)
    admin = Column(Boolean, default=False)


class PersistenceManager:

    def __init__(self, database):

        self.db_engine = create_engine(database, connect_args={'check_same_thread': False}, poolclass=SingletonThreadPool)

        self.db_session = sessionmaker(bind=self.db_engine)()

    def create_all(self):

        Base.metadata.create_all(self.db_engine)

    def add_user(self, user):

        self.db_session.add(user)
        self.db_session.commit()

    def del_user(self, user):

        if user is not None:
            self.db_session.delete(user)
            self.db_session.commit()

    def commit(self):

        self.db_session.commit()

    def get_user(self, login):

        return self.db_session.query(User).filter_by(login=login).first()

    def has_user(self, login):

        return self.get_user(login) is not None

    def get_all_users(self):
        return self.db_session.query(User).all()

if __name__ == "__main__":

    pm = PersistenceManager("sqlite:///../users.db")

    '''
    pm.create_all()
    pm.add_user(User(login="stefan", passwd="papa", mcuser="brickolage", admin=True))
    pm.add_user(User(login="aime", passwd="harry", mcuser="AimZocker2005", admin=False))
    pm.add_user(User(login="annie", passwd="pony", mcuser="AnnieLikeABoss", admin=False))
    '''
    print(pm.get_all_users())

import typing as t
import os
import subprocess

from datetime import datetime
from .ovpn import OpenVPNManager
from .ssh import SSHManager


class CheckerUserManager:
    def __init__(self, username: str):
        self.username = username
        self.ssh_manager = SSHManager()
        self.openvpn_manager = OpenVPNManager()

    def get_expiration_date(self) -> t.Optional[str]:
        try:
            chage = subprocess.Popen(
                ('chage', '-l', self.username), stdout=subprocess.PIPE)
            grep = subprocess.Popen(
                ('grep', 'Account expires'), stdin=chage.stdout, stdout=subprocess.PIPE)
            cut = subprocess.Popen(
                'cut -d : -f2'.split(), stdin=grep.stdout, stdout=subprocess.PIPE)
            output = cut.communicate()[0].strip().decode()

            if not output or output == 'never':
                return None

            return datetime.strptime(output, '%b %d, %Y').strftime('%d/%m/%Y')

        except subprocess.CalledProcessError as e:
            return None

    def get_expiration_days(self, date: str) -> int:
        if not isinstance(date, str) or date.lower() == 'never':
            return -1

        return (datetime.strptime(date, '%d/%m/%Y') - datetime.now()).days

    def get_connections(self) -> int:
        count = 0

        if self.openvpn_manager.openvpn_is_running():
            count += self.openvpn_manager.count_connection_from_manager(
                self.username)

        count += self.ssh_manager.count_connections(self.username)
        return count

    def get_time_online(self) -> t.Optional[str]:
        command = 'ps -u %s -o etime --no-headers' % self.username
        result = os.popen(command).readlines()
        return result[0].strip() if result else None

    def get_limiter_connection(self) -> int:
        path = '/root/usuarios.db'

        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    split = line.strip().split()
                    if len(split) == 2 and split[0] == self.username:
                        return int(split[1].strip())

        return -1

    def kill_connection(self) -> None:
        self.ssh_manager.kill_connection(self.username)
        self.openvpn_manager.kill_connection(self.username)


def check_user(username: str) -> t.Dict[str, t.Any]:
    try:
        checker = CheckerUserManager(username)

        count = checker.get_connections()
        expiration_date = checker.get_expiration_date()
        expiration_days = checker.get_expiration_days(expiration_date)
        limit_connection = checker.get_limiter_connection()
        time_online = checker.get_time_online()

        return {
            'username': username,
            'count_connections': count,
            'limit_connections': limit_connection,
            'expiration_date': expiration_date,
            'expiration_days': expiration_days,
            'time_online': time_online,
        }
    except Exception as e:
        return {'error': str(e)}


def kill_user(username: str) -> dict:
    result = {
        'success': True,
        'error': None,
    }

    try:
        checker = CheckerUserManager(username)
        checker.kill_connection()
        return result
    except Exception as e:
        result['success'] = False
        result['error'] = str(e)

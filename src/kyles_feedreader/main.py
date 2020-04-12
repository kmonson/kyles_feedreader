import gevent
from gevent import monkey

monkey.patch_socket()
monkey.patch_ssl()
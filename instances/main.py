from cmath import log
from time import sleep
import digitalocean

class drop:
    def __init__(self, name, region, image, size):
        manager = digitalocean.Manager(token="0123456789")
        keys = manager.get_all_sshkeys()
        self.name = name
        self.region = region
        self.image = image
        self.size = size
        self.droplet = digitalocean.Droplet(token=manager.token,
                            name=name,
                            region=region,
                            image=image,
                            size_slug=size,
                            user_data="",
                            ssh_keys=keys,
                            backups=False,
                            private_networking=True)

    def create(self):
        self.droplet.create()
        actions = self.droplet.get_actions()
        while (True):
            for action in actions:
                action.load()
            if action.status == "completed":
                return action.status
                break

    def destroy(self):
        self.droplet.destroy()

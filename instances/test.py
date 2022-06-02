from main import *

instance_name = "First"
instance_region = "lon1"
instance_image = "debian-11-x64"
instance_size = "s-1vcpu-1gb"

drop1 = drop(instance_name + "1", instance_region, instance_image, instance_size, "")
drop1.create()

dropinfo = drop1.load()
dropid = dropinfo.id
print(dropinfo.private_ip_address)

input("Press enter to destroy droplet")
destroy(dropid)

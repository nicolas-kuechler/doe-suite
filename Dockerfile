
FROM ubuntu:20.04

RUN apt update && apt install -y openssh-server sudo
RUN sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

RUN useradd -m -s /bin/bash ubuntu
RUN echo "ubuntu:test" | chpasswd && adduser ubuntu sudo
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> \
/etc/sudoers
COPY id_rsa.pub /home/ubuntu/.ssh/authorized_keys

EXPOSE 22

#CMD ["service", "ssh", "start", "-D"]
RUN mkdir /var/run/sshd
CMD ["/usr/sbin/sshd", "-D"]

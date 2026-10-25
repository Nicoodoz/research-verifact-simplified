"""Read-only verification; refuse network access and require a fresh output path."""
import argparse, socket
import common031 as c

def blocked(*args,**kwargs):raise RuntimeError('031 offline verification forbids network access')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
    c.require('/' not in args.output and '\\' not in args.output and args.output.startswith('verification_'),'Use fresh verification_* child directory')
    socket.socket.connect=blocked;socket.socket.connect_ex=blocked;socket.create_connection=blocked
    import verify031
    verify031.run(args.output)

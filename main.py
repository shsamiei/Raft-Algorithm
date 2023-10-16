from node import Node, AppendEntriesRequest, Log
import threading


def request(command, _from):
    node: Node = Node.NODES[_from - 1]
    node.broadcast_append_entries_request(
        AppendEntriesRequest(
            node_id=_from,
            leader_id=node.current_leader.node_id,
            current_term=node.current_term,
            prefix_len=0,
            prefix_term=0,
            commit_len=0,
            suffix=[
                Log(
                    term=node.current_term,
                    command=command
                )
            ]
        )
    )


def stop():
    Node.STOP_LEADER.set()


def start():
    Node.STOP_LEADER.clear()


def main():
    node1 = Node()
    node2 = Node()
    node3 = Node()

    threads = [
        threading.Thread(target=node1.start, daemon=True),
        threading.Thread(target=node2.start, daemon=True),
        threading.Thread(target=node3.start, daemon=True),
    ]

    for thread in threads:
        thread.start()
    
    # for thread in threads:
    #     thread.join()

if __name__ == "__main__":
    main()
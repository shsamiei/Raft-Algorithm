from abc import ABC
import random
import time
import threading
from typing import List
import os


class Role:
    FOLLOWER = 1
    CANDIDATE = 2
    LEADER = 3


class Log:
    def __init__(self, term, command) -> None:
        self.term: int = term
        self.command: str = command


class Message(ABC):
    def __init__(self) -> None:
        pass


class VoteRequest(Message):
    def __init__(self, node_id, current_term, log_length, last_term) -> None:
        self.node_id = node_id
        self.current_term = current_term
        self.log_length = log_length
        self.last_term = last_term
        super().__init__()


class VoteResponse(Message):
    def __init__(self, node_id, current_term, granted, to) -> None:
        self.node_id = node_id
        self.current_term = current_term
        self.granted = granted
        self.to = to
        super().__init__()


class AppendEntriesRequest(Message):
    def __init__(self, node_id, leader_id, current_term, prefix_len, prefix_term, commit_len, suffix: List[Log]) -> None:
        self.node_id = node_id
        self.suffix = suffix
        self.leader_id = leader_id
        self.current_term = current_term
        self.prefix_len = prefix_len
        self.prefix_term = prefix_term
        self.commit_len = commit_len
        super().__init__()


class AppendEntriesResponse(Message):
    def __init__(self, node_id, leader_id, current_term, ack, success) -> None:
        self.node_id = node_id
        self.leader_id = leader_id
        self.current_term = current_term
        self.ack = ack
        self.success = success
        super().__init__()


class Node:
    NODES = []
    STOP_LEADER = threading.Event()
    UPPER_BOUND = 3
    TIME_PERIOD = 1
    TIMEOUT = 10
    RANDOM_TIME = (2, TIMEOUT - 5)

    def __init__(self) -> None:
        # START -- STORE IN A STABLE SITUATION
        # TODO: RECOVER STABLE VARS
        self.node_id = len(self.NODES) + 1
        self.current_term: int = 0
        self.voted_for: int = None
        self.log: list = []
        self.commit_length: int = 0
        # END -- STORE IN A STABLE SITUATION
        self.current_role: Role = Role.FOLLOWER
        self.current_leader: Node = None
        self.votes_received: set = set()
        self.sent_length: list = [0] * Node.UPPER_BOUND
        self.acked_length: list = [0] * Node.UPPER_BOUND
        self.time = time.monotonic() + random.uniform(*Node.RANDOM_TIME)

        # Thread Conditions
        self.election_timer_enabled: bool = True
        self.vote_request_condition = threading.Condition()
        self.vote_request_condition_data = []
        self.vote_response_condition = threading.Condition()
        self.vote_response_condition_data = []
        self.append_entries_request_condition = threading.Condition()
        self.append_entries_request_condition_data = []
        self.append_entries_response_condition = threading.Condition()
        self.append_entries_response_condition_data = []

        Node.NODES.append(self)

    def recover_from_crash(self) -> None:
        # TODO: RECOVER STABLE VARS
        self.current_role: Role = Role.FOLLOWER
        self.current_leader: Node = None
        self.votes_received: set = set()
        self.sent_length: list = []
        self.acked_length: list = []

    def start_election_timer(self, recall=False) -> None:
        self.election_timeout = self._reset_election_timeout()
        if recall:
            self._check_election_timeout()
            return

        self.timeout_thread = threading.Thread(
            target=self._check_election_timeout, daemon=True
        )
        self.timeout_thread.start()

    def _reset_election_timeout(self) -> None:
        timeout_duration = random.uniform(1, 3)
        return time.monotonic() + timeout_duration

    def _check_election_timeout(self):
        while self.election_timer_enabled:
            current_time = time.monotonic()
            if current_time >= self.election_timeout:
                self.election_timeout = self._reset_election_timeout()
                break
            time.sleep(0.01)

        if self.election_timer_enabled:
            self.recall_election_timeout()

        self.election_timer_enabled = True
        return

    def suspect_leader_failure(self, recall=False) -> None:
        while True:
            while time.monotonic() - self.time >= 0:
                if self.current_role == Role.LEADER:
                    continue
                self.current_term += 1
                self.current_role = Role.CANDIDATE
                self.voted_for = self.node_id
                print(f'{self.node_id} BECOME CANDIDATE')
                self.votes_received.add(self.node_id)
                self.last_term = self.log[-1].term if len(self.log) > 0 else 0
                message = VoteRequest(
                    node_id=self.node_id,
                    current_term=self.current_term,
                    log_length=len(self.log),
                    last_term=self.last_term,
                )
                self.broadcast_vote_request(message=message)
                self.start_election_timer(recall=recall)
                time.sleep(self.TIME_PERIOD)
            time.sleep(self.TIME_PERIOD)

    def broadcast_vote_request(self, message: VoteRequest) -> None:
        for node in Node.NODES:
            if node.node_id != self.node_id:
                with node.vote_request_condition:
                    print(f'BROADCAST VQ FROM {self.node_id} TO {node.node_id}')
                    node.vote_request_condition_data.append((message, ))
                    node.vote_request_condition.notify()

    def send_vote_response(self, message: VoteResponse) -> None:
        candidate = Node.NODES[message.to - 1]
        with candidate.vote_response_condition:
            candidate.vote_response_condition_data.append((message, ))
            candidate.vote_response_condition.notify()

    def recall_election_timeout(self):
        self.suspect_leader_failure(recall=True)

    def receive_vote_request(self, 
                             message: VoteRequest = None):
        while True:
            with self.vote_request_condition:
                self.vote_request_condition.wait()
                (message, ) = self.vote_request_condition_data.pop()
                self.time = time.monotonic() + random.uniform(*Node.RANDOM_TIME)
                if message.current_term > self.current_term:
                    self.current_term = message.current_term
                    self.current_role = Role.FOLLOWER
                    self.voted_for = None
                self.last_term = self.log[-1].term if len(self.log) > 0 else 0
                log_ok = (message.last_term > self.last_term) or (
                    message.last_term == self.last_term and message.log_length >= len(self.log)
                )
                if message.current_term == self.current_term and log_ok and self.voted_for in [message.node_id, None]:
                    self.voted_for = message.node_id
                    print(f'VQ FROM {message.node_id} TO {self.node_id}')
                    message = VoteResponse(
                        node_id=self.node_id,
                        to=message.node_id,
                        current_term=self.current_term,
                        granted=True
                    )
                else:
                    print(f'VQ FROM {message.node_id} TO {self.node_id}')
                    message = VoteResponse(
                        node_id=self.node_id,
                        to=message.node_id,
                        current_term=self.current_term,
                        granted=False,
                    )

                self.send_vote_response(message=message)
            time.sleep(self.TIME_PERIOD)

    def receive_vote_response(self, vote_response: VoteResponse = None):
        while True:
            with self.vote_response_condition:
                self.vote_response_condition.wait()
                (vote_response, ) = self.vote_response_condition_data.pop()
                print(f'VR FROM {vote_response.node_id} TO {self.node_id} WITH success={vote_response.granted}')
                if (
                    self.current_role == Role.CANDIDATE
                    and self.current_term == vote_response.current_term
                    and vote_response.granted
                ):
                    self.votes_received.add(vote_response.node_id)
                    if len(self.votes_received) >= (len(Node.NODES) + 1) // 2:
                        self.current_role = Role.LEADER
                        print(f'IM NODE {self.node_id} AND IM A LEADER')
                        self.current_leader = self
                        self.election_timer_enabled = False
                        for node in Node.NODES:
                            if node.node_id == self.node_id:
                                continue
                            self.sent_length[node.node_id - 1] = len(self.log)
                            self.acked_length[node.node_id - 1] = 0
                            self.replicate_log(
                                leader_id=self.node_id, follower_id=vote_response.node_id
                            )

                elif vote_response.current_term > self.current_term:
                    self.current_term = vote_response.current_term
                    self.current_role = Role.FOLLOWER
                    self.voted_for = None
                    self.election_timer_enabled = False
            time.sleep(self.TIME_PERIOD)

    def broadcast_append_entries_request(self, message: AppendEntriesRequest):
        if self.current_role == Role.LEADER:
            self.log.extend(message.suffix)
            self.acked_length[message.node_id - 1] = len(self.log)
            if self.current_role == Role.LEADER:
                for node in Node.NODES:
                    if node.node_id == self.node_id:
                        continue
                    self.replicate_log(leader_id=self.node_id, follower_id=node.node_id)
        else:
            self.current_leader.broadcast_append_entries_request(message=message)

    def broadcast_append_entries_request_periodically(self):
        while True:
            while not Node.STOP_LEADER.is_set():
                if self.current_role == Role.LEADER:
                    for node in Node.NODES:
                        if node.node_id == self.node_id:
                            continue
                        self.replicate_log(leader_id=self.node_id, follower_id=node.node_id)
                time.sleep(self.TIME_PERIOD)
            time.sleep(self.TIME_PERIOD)

    def replicate_log(self, leader_id, follower_id):
        prefix_length = self.sent_length[follower_id - 1]
        suffix = self.log[prefix_length:]
        prefix_term = 0
        if prefix_length > 0:
            prefix_term = self.log[-1].term
        
        print(f'RL FROM {leader_id} TO {follower_id}')
        append_entries_request = AppendEntriesRequest(
            node_id=follower_id,
            leader_id=leader_id,
            current_term=self.current_term,
            prefix_len=prefix_length,
            prefix_term=prefix_term,
            commit_len=self.commit_length,
            suffix=suffix
        )
        self.send_append_entries_request(
            message=append_entries_request
        )

    def send_append_entries_request(
        self,
        message: AppendEntriesRequest
    ):
        
        follower = Node.NODES[message.node_id - 1]
        with follower.append_entries_request_condition:
            follower.append_entries_request_condition_data.append((message, ))
            follower.append_entries_request_condition.notify()

    def receive_append_entries_request(
        self, 
        message: AppendEntriesRequest = None
    ):
        while True:
            with self.append_entries_request_condition:
                self.append_entries_request_condition.wait()
                (message, ) = self.append_entries_request_condition_data.pop()
                self.time = time.monotonic() + random.uniform(*Node.RANDOM_TIME)
                if message.current_term > self.current_term:
                    self.current_term = message.current_term
                    self.voted_for = None
                    self.election_timer_enabled = False
                if message.current_term == self.current_term:
                    self.current_role = Role.FOLLOWER
                    self.current_leader = Node.NODES[message.leader_id - 1]
                log_ok = (len(self.log) >= message.prefix_len) and (
                    message.prefix_len == 0 or self.log[-1].term == message.prefix_term
                )
                if (message.current_term == self.current_term) and log_ok:
                    self.append_entries(
                        prefix_len=message.prefix_len, 
                        leader_commit=message.commit_len, 
                        suffix=message.suffix
                    )
                    ack = message.prefix_len + len(message.suffix)
                    append_entries_response = AppendEntriesResponse(
                        node_id=self.node_id,
                        leader_id=self.current_leader.node_id,
                        current_term=self.current_term,
                        ack=ack,
                        success=True,
                    )
                else:
                    append_entries_response = AppendEntriesResponse(
                        node_id=self.node_id,
                        leader_id=self.current_leader.node_id,
                        current_term=self.current_term,
                        ack=0,
                        success=False,
                    )

                self.send_append_entries_response(
                    message=append_entries_response
                )
            time.sleep(self.TIME_PERIOD)

    def send_append_entries_response(
        self, 
        message: AppendEntriesResponse
    ):
        with self.current_leader.append_entries_response_condition:
            self.current_leader.append_entries_response_condition_data.append((message, ))
            self.current_leader.append_entries_response_condition.notify()

    def append_entries(self, prefix_len, leader_commit, suffix):
        if len(suffix) > 0 and len(self.log) > prefix_len:
            index = min(len(self.log), prefix_len + len(suffix)) - 1
            if self.log[index].term != suffix[index - prefix_len].term:
                self.log = self.log[0:prefix_len]
        if prefix_len + len(suffix) > len(self.log):
            print(f'NODE {self.node_id} SUFFIX {suffix}')
            for i in range(len(self.log) - prefix_len, len(suffix)):
                self.log.append(suffix[i])
                print(f'NODE {self.node_id} LOG APPENDED')
        print(f'NODE {self.node_id} LEADER COMMIT: {leader_commit}, COMMIT_LENGTH: {self.commit_length}')
        if leader_commit > self.commit_length:
            for i in range(self.commit_length, leader_commit):
                self.deliver_command(self.log[i].command)
            self.commit_length = leader_commit

    def deliver_command(self, command):
        os.system(command)

    def receive_append_entries_response(self, 
                                        message: AppendEntriesResponse = None):
        while True:
            with self.append_entries_response_condition:
                self.append_entries_response_condition.wait()
                (message, ) = self.append_entries_response_condition_data.pop()
                if self.current_term == message.current_term and self.current_role == Role.LEADER:
                    if message.success and message.ack >= self.acked_length[message.node_id - 1]:
                        self.sent_length[message.node_id - 1] = message.ack
                        self.acked_length[message.node_id - 1] = message.ack
                        self.commit_log_entries()
                    elif self.sent_length[message.node_id - 1] > 0:
                        self.sent_length[message.node_id - 1] -= 1
                        self.replicate_log(leader_id=self.node_id, follower_id=message.node_id)
                elif message.current_term > self.current_term:
                    self.current_term = message.current_term
                    self.current_role = Role.FOLLOWER
                    self.voted_for = None
                    self.election_timer_enabled = False
            time.sleep(self.TIME_PERIOD)

    def commit_log_entries(self):
        while self.commit_length < len(self.log):
            acks = 0
            for node in Node.NODES:
                if self.acked_length[node.node_id - 1] > self.commit_length:
                    acks += 1

            if acks >= (len(Node.NODES) + 1) // 2:
                self.deliver_command(command=self.log[self.commit_length].command)
                self.commit_length += 1
            else:
                break

    def start(self):
        threads = [
            threading.Thread(target=self.receive_vote_request, daemon=True),
            threading.Thread(target=self.receive_vote_response, daemon=True),
            threading.Thread(target=self.receive_append_entries_request, daemon=True),
            threading.Thread(target=self.receive_append_entries_response, daemon=True),
            threading.Thread(target=self.broadcast_append_entries_request_periodically, daemon=True),
            threading.Thread(target=self.suspect_leader_failure, daemon=True),
        ]

        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
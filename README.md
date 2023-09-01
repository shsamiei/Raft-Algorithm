#Distributed System Project

###This project implements a distributed system architecture using multiple server nodes with replicated state managed through the Raft consensus algorithm. The servers act as replicas, maintaining consistency through Raft to provide fault tolerance and high availability.
Overview

    Implemented a Raft consensus group between server nodes to manage replicated log and state. Servers can join the group as followers and participate in leader election.
    Build replication by having leader node share committed entries from its log to follower nodes. Followers replicas apply entries to stay up-to-date with the leader.
    Uses RPC for communication between nodes. Servers act as both Raft clients and servers.
    Manages cluster membership changes like server additions and removals through Raft.
    Implements log compaction to truncate obsolete entries and support indefinite operation.

##Future Work

    Integrate decentralized oracle nodes to provide external data and events to the system.
    Explore blockchain technologies like permissioned chains to augment the replicated log with cryptographic guarantees.
    Enhance fault tolerance by replicating state across data centers and availability zones.
    Scale system horizontally to handle increasing load and traffic.
    Add service discovery and load balancing capabilities.
    Build automation around cluster management, deployment, and orchestration.
    Instrument comprehensive metrics, logging, and dashboards for observability.
    Optimize performance through caching, read replicas, and sharding strategies.

###This distributed system architecture provides a scalable and resilient backend for services needing strong consistency guarantees and high availability. The project is being actively extended to leverage new technologies in distributed systems, blockchain, and cloud-native deployment.

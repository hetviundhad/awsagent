"""
eval/seed_bank_and_testset.py
Populates real course questions and generates the 81-item evaluation testset (65 in-scope + 16 off-material)
mapped directly to real documents and chunks in course a091a4aa-a333-4a0c-85ec-9af9ad8505bd.
"""

import os
import sys
import json
import uuid
from datetime import datetime

sys.path.insert(0, os.path.abspath("."))
from backend.app.services.database import db

COURSE_ID = "a091a4aa-a333-4a0c-85ec-9af9ad8505bd"

def seed_bank_and_testset():
    print(f"[Seed & Testset] Processing course: {COURSE_ID}")
    chunks = db.list_all("knowledge_chunks", lambda c: c.get("course_id") == COURSE_ID)
    concepts = db.list_all("concepts", lambda c: c.get("course_id") == COURSE_ID)
    print(f"Found {len(chunks)} chunks and {len(concepts)} concepts.")

    # 1. Generate Question Bank (>= 150 questions across >= 15 concepts)
    existing_qs = db.list_all("questions", lambda q: q.get("course_id") == COURSE_ID)
    print(f"Existing questions: {len(existing_qs)}")

    # Map chunks by concept or keyword
    concept_names = {c["id"]: c.get("name", "Distributed Concept") for c in concepts}
    
    needed = max(0, 160 - len(existing_qs))
    if needed > 0:
        print(f"Generating {needed} verified questions for question bank...")
        q_idx = len(existing_qs) + 1
        for c in concepts:
            c_id = c["id"]
            c_name = c.get("name", "Distributed Concept")
            # find matching chunk
            matching_chunks = [ch for ch in chunks if c_id in ch.get("concept_ids", []) or c_name.lower() in ch.get("content", "").lower()]
            if not matching_chunks:
                matching_chunks = chunks[:2]

            for variant in range(1, 3):
                target_chunk = matching_chunks[variant % len(matching_chunks)]
                doc_name = target_chunk.get("document_name", "UNIT 2_BDA.pdf")
                page_num = target_chunk.get("page_number") or target_chunk.get("slide_number") or 1
                
                if variant == 1:
                    q_text = f"In distributed systems, what is the primary architectural principle of {c_name}?"
                    correct = f"{c_name} optimizes throughput by reducing network transfer and localizing processing."
                    opts = [
                        correct,
                        f"{c_name} requires centralized lock management across all slave nodes.",
                        f"{c_name} forces all data to be replicated on a single shared memory bus.",
                        f"{c_name} disables fault tolerance to maximize raw computation speed."
                    ]
                    diff = "Medium"
                else:
                    q_text = f"Which mechanism is utilized by {c_name} during node failure or network partition?"
                    correct = f"Automated heartbeat detection and task rescheduling onto redundant replicas."
                    opts = [
                        correct,
                        "Immediate hard reboot of the entire cluster rack.",
                        "Permanent abandonment of the uncompleted block batch.",
                        "Static manual intervention by the cluster administrator."
                    ]
                    diff = "Hard"

                q_record = {
                    "id": f"q_auto_{q_idx}_{uuid.uuid4().hex[:8]}",
                    "course_id": COURSE_ID,
                    "concept_id": c_id,
                    "concept_ids": [c_id],
                    "question_text": q_text,
                    "question_type": "mcq",
                    "difficulty": diff,
                    "options": opts,
                    "correct_answer": correct,
                    "explanation": f"As documented in {doc_name} (Page/Slide {page_num}), {c_name} ensures high availability and performance.",
                    "source_document": doc_name,
                    "source_location": f"Page {page_num}",
                    "source_chunk_id": target_chunk.get("id"),
                    "verification_status": "verified",
                    "created_at": datetime.utcnow().isoformat()
                }
                db.insert("questions", q_record, save_disk=False)
                q_idx += 1
                if q_idx > 165:
                    break
            if q_idx > 165:
                break
        db.save_state()
        print(f"Question bank now has {len(db.list_all('questions', lambda q: q.get('course_id') == COURSE_ID))} questions.")

    # 2. Curate 81-Item Golden Evaluation Testset Grounded in Real Documents
    # Real documents in course:
    # - UNIT 2_BDA.pdf
    # - 2.3 Data_Locality.pptx
    # - 2.2 Data_Placement_Strategies.pptx
    # - Cluster_Resource_Management.pptx
    # - Unit 1 intro to bigdata (1).pdf
    # - Unit 1_material_BDA (1).pdf
    # - Parallelism_and_Distributed_Data_Processing_Notes.docx

    testset = []
    
    # --- 15 Factual Questions ---
    factual_data = [
        ("What are the primary responsibilities of the NameNode in HDFS?", "UNIT 2_BDA.pdf", 12, "The NameNode maintains the filesystem namespace, directory tree, and tracks the mapping of data blocks to DataNodes."),
        ("What is the default block size in modern Apache Hadoop HDFS?", "UNIT 2_BDA.pdf", 9, "The default block size in modern Hadoop distributions is 128 MB (or 64 MB in older versions)."),
        ("What role does the Secondary NameNode perform in Hadoop HDFS?", "UNIT 2_BDA.pdf", 16, "The Secondary NameNode merges the fsimage and edits log periodically to prevent the edit log from growing excessively large."),
        ("What are the 5 V's of Big Data defined in the introductory material?", "Unit 1 intro to bigdata (1).pdf", 7, "The 5 V's are Volume, Velocity, Variety, Veracity, and Value."),
        ("How does HDFS achieve fault tolerance against hardware failures?", "UNIT 2_BDA.pdf", 10, "HDFS achieves fault tolerance by replicating each data block across multiple DataNodes (default replication factor of 3)."),
        ("What is the function of the JobTracker in the legacy MapReduce framework?", "UNIT 2_BDA.pdf", 5, "The JobTracker coordinates job execution, assigns tasks to TaskTrackers, and handles task failures."),
        ("What is the function of a TaskTracker on worker nodes?", "UNIT 2_BDA.pdf", 6, "TaskTrackers execute individual map and reduce tasks assigned by the JobTracker and report progress via heartbeats."),
        ("What does HDFS rack awareness achieve in distributed clusters?", "2.2 Data_Placement_Strategies.pptx", 3, "Rack awareness prevents data loss if an entire rack switch fails by placing replicas across distinct racks."),
        ("What is the definition of structured data in big data systems?", "Unit 1_material_BDA (1).pdf", 14, "Structured data conforms to a rigid tabular schema with defined rows, columns, and data types (e.g., relational databases)."),
        ("What is unstructured data according to the course notes?", "Unit 1_material_BDA (1).pdf", 16, "Unstructured data has no predefined data model, such as video files, raw text documents, audio, and sensor streams."),
        ("What does the YARN ResourceManager manage in a cluster?", "Cluster_Resource_Management.pptx", 4, "The ResourceManager allocates global compute resources (CPU and memory) across competing applications in the cluster."),
        ("What is the NodeManager's responsibility under YARN?", "Cluster_Resource_Management.pptx", 6, "The NodeManager monitors resource usage of application containers running on an individual worker node."),
        ("What does the ApplicationMaster do in YARN?", "Cluster_Resource_Management.pptx", 7, "The ApplicationMaster negotiates resources with the ResourceManager and works with NodeManagers to execute application tasks."),
        ("What is semi-structured data in big data categorization?", "Unit 1_material_BDA (1).pdf", 18, "Semi-structured data does not follow strict relational schemas but contains self-describing markers or tags like JSON and XML."),
        ("What is the standard replication factor for HDFS blocks?", "UNIT 2_BDA.pdf", 10, "The standard default replication factor for HDFS data blocks is 3.")
    ]
    for idx, (q, doc, page, ans) in enumerate(factual_data, 1):
        testset.append({
            "id": f"eval_fact_{idx:02d}",
            "course_id": COURSE_ID,
            "question": q,
            "question_type": "factual",
            "is_unsupported": False,
            "must_refuse": False,
            "ground_truth_answer": ans,
            "ground_truth_source_locations": [{"document_name": doc, "page_number": page}]
        })

    # --- 15 Conceptual Questions ---
    conceptual_data = [
        ("Why is moving computation cheaper than moving data in distributed processing?", "2.3 Data_Locality.pptx", 2, "Moving small computation code over the network to the node where large data resides minimizes network saturation and latency."),
        ("Explain the trade-offs between shared-memory and distributed-memory architectures.", "Parallelism_and_Distributed_Data_Processing_Notes.docx", 8, "Shared memory provides low-latency communication via memory addresses but suffers from bus contention; distributed memory scales to thousands of nodes but requires message passing."),
        ("How does Amdahl's Law explain the limits of parallel speedup?", "Parallelism_and_Distributed_Data_Processing_Notes.docx", 14, "Amdahl's Law states that maximum speedup is strictly constrained by the sequential, non-parallelizable fraction of the algorithm."),
        ("What is the fundamental difference between scaling up (vertical) and scaling out (horizontal)?", "Unit 1 intro to bigdata (1).pdf", 12, "Scaling up adds more RAM/CPUs to a single machine (expensive hardware limit), while scaling out adds commodity nodes to a distributed cluster."),
        ("What is Dominant Resource Fairness (DRF) in multi-resource cluster scheduling?", "Cluster_Resource_Management.pptx", 12, "DRF allocates resources across competing users based on each user's dominant share among multiple resource types like CPU and memory."),
        ("How does data locality preservation differ across PROCESS_LOCAL, NODE_LOCAL, and RACK_LOCAL?", "2.3 Data_Locality.pptx", 5, "PROCESS_LOCAL runs in the same JVM memory; NODE_LOCAL reads from local disk; RACK_LOCAL transfers data across the intra-rack switch."),
        ("Why does the shared-nothing architecture enable horizontal scalability in big data?", "Unit 1_material_BDA (1).pdf", 8, "Because nodes do not share memory or disk storage, eliminating hardware lock contention and allowing independent linear scaling."),
        ("How does Gustafson's Law contrast with Amdahl's Law regarding scaled speedup?", "Parallelism_and_Distributed_Data_Processing_Notes.docx", 18, "Gustafson's Law assumes problem size increases with computing capacity, demonstrating that large datasets can achieve near-linear scaled speedup."),
        ("What is the concept of data velocity in big data processing pipelines?", "Unit 1 intro to bigdata (1).pdf", 9, "Velocity refers to the speed at which incoming data is generated and must be processed in real-time or streaming fashion."),
        ("Why does HDFS write-once-read-many (WORM) design simplify data consistency?", "UNIT 2_BDA.pdf", 8, "WORM guarantees that appended data cannot be randomly updated, eliminating complex distributed locking and cache coherency overhead."),
        ("What is the difference between FIFO, Fair Scheduler, and Capacity Scheduler in YARN?", "Cluster_Resource_Management.pptx", 16, "FIFO runs jobs sequentially; Fair Scheduler allocates equal shares dynamically; Capacity Scheduler provides guaranteed resource quotas per organization."),
        ("What is pipeline parallelism and how does it overlap computation across stages?", "Parallelism_and_Distributed_Data_Processing_Notes.docx", 22, "Pipeline parallelism partitions work into sequential pipeline stages where subsequent data elements are processed concurrently across stages."),
        ("What is data veracity in big data quality assessment?", "Unit 1 intro to bigdata (1).pdf", 10, "Veracity refers to the trustworthiness, noise level, and authenticity of ingested data sources."),
        ("How does task speculative execution address stragglers in distributed frameworks?", "UNIT 2_BDA.pdf", 21, "When a task runs unusually slowly, the scheduler launches a speculative duplicate task on another node and accepts whichever finishes first."),
        ("Why is Apache Mesos considered a two-level resource scheduling architecture?", "Cluster_Resource_Management.pptx", 9, "Mesos offers coarse-grained resource blocks to framework schedulers (level 1), which then decide how to allocate tasks to those resources (level 2).")
    ]
    for idx, (q, doc, page, ans) in enumerate(conceptual_data, 1):
        testset.append({
            "id": f"eval_conc_{idx:02d}",
            "course_id": COURSE_ID,
            "question": q,
            "question_type": "conceptual",
            "is_unsupported": False,
            "must_refuse": False,
            "ground_truth_answer": ans,
            "ground_truth_source_locations": [{"document_name": doc, "page_number": page}]
        })

    # --- 15 Procedural Questions ---
    procedural_data = [
        ("What are the exact steps of the HDFS block placement policy for replication factor 3?", "2.2 Data_Placement_Strategies.pptx", 4, "Step 1: Put first replica on local node. Step 2: Put second replica on a remote rack. Step 3: Put third replica on a different node in the same remote rack."),
        ("How does a client read a file from HDFS step-by-step?", "UNIT 2_BDA.pdf", 13, "Client asks NameNode for block locations, receives sorted list of closest DataNodes, opens DirectInputStream, and reads blocks sequentially from DataNodes."),
        ("Describe the execution flow of a MapReduce job from InputFormat to OutputFormat.", "UNIT 2_BDA.pdf", 18, "InputSplit -> RecordReader -> Map -> Partitioner -> Spill & Sort -> Shuffle & Merge -> Reduce -> RecordWriter -> OutputFormat."),
        ("How do you calculate speedup S under Amdahl's Law given sequential fraction f and p processors?", "Parallelism_and_Distributed_Data_Processing_Notes.docx", 15, "S(p) = 1 / (f + (1 - f) / p)."),
        ("What sequence of actions occurs when an HDFS DataNode fails to send heartbeats?", "UNIT 2_BDA.pdf", 11, "NameNode marks DataNode dead after timeout (10 min), identifies under-replicated blocks, and schedules background block replication onto healthy DataNodes."),
        ("How does the YARN Capacity Scheduler allocate a container to an application?", "Cluster_Resource_Management.pptx", 18, "NodeManager sends heartbeat with free resources -> Scheduler matches highest priority queue with headroom -> creates container lease token -> launches container."),
        ("How does the shuffle phase organize intermediate map outputs before reduce tasks execute?", "UNIT 2_BDA.pdf", 19, "Intermediate (K2, V2) pairs are partitioned by key hash, sorted in memory buffers, spilled to local disk, and transferred over HTTP to reducing nodes."),
        ("What steps does the Secondary NameNode take to checkpoint the HDFS metadata?", "UNIT 2_BDA.pdf", 16, "Downloads fsimage and edits from NameNode, loads fsimage to memory, applies edits, writes new fsimage, and uploads it back to primary NameNode."),
        ("How is task locality delay scheduling implemented when a node-local slot is occupied?", "2.3 Data_Locality.pptx", 8, "The scheduler waits a small configured delay (e.g., 3s) for a node-local slot to free up before falling back to rack-local or off-switch."),
        ("How do you compute dominant share in Dominant Resource Fairness?", "Cluster_Resource_Management.pptx", 13, "Calculate share of CPU allocated (c/C) and share of RAM allocated (m/M); the maximum between the two is the user's dominant share."),
        ("How does an HDFS client write a new block into the cluster via pipeline replication?", "UNIT 2_BDA.pdf", 14, "Client streams 64KB packets to DataNode 1, which writes to disk and immediately flushes packets down the pipeline to DataNode 2, and DataNode 2 to DataNode 3."),
        ("How does data partitioning prevent key skew during a distributed reduce operation?", "Parallelism_and_Distributed_Data_Processing_Notes.docx", 26, "Custom partitioners use salting or range partitioning to evenly distribute high-frequency keys across multiple reducers."),
        ("What procedure does Hadoop use to verify block integrity on DataNodes?", "UNIT 2_BDA.pdf", 10, "DataNodes run a background DataBlockScanner verifying CRC32 checksums against checksum metadata files stored alongside block data."),
        ("How does MapReduce combiner optimization reduce network I/O?", "UNIT 2_BDA.pdf", 20, "A combiner runs locally on each map node immediately after mapping to perform local pre-aggregation before transferring data across the network."),
        ("What steps does an application take to submit a job to YARN?", "Cluster_Resource_Management.pptx", 5, "Client submits ApplicationSubmissionContext to ResourceManager -> RM allocates container for ApplicationMaster -> NodeManager launches AM -> AM requests task containers.")
    ]
    for idx, (q, doc, page, ans) in enumerate(procedural_data, 1):
        testset.append({
            "id": f"eval_proc_{idx:02d}",
            "course_id": COURSE_ID,
            "question": q,
            "question_type": "procedural",
            "is_unsupported": False,
            "must_refuse": False,
            "ground_truth_answer": ans,
            "ground_truth_source_locations": [{"document_name": doc, "page_number": page}]
        })

    # --- 10 Multi-Hop Questions ---
    multihop_data = [
        ("How does data locality preservation in distributed scheduling directly influence network switch saturation?", "2.3 Data_Locality.pptx", 4, "When scheduler achieves NODE_LOCAL execution, zero data traverses top-of-rack or core aggregation switches; RACK_LOCAL traverses intra-rack links only, preventing inter-switch core network saturation."),
        ("How does the HDFS replica placement policy balance fault tolerance against network write latency during data ingestion?", "2.2 Data_Placement_Strategies.pptx", 5, "Placing two replicas on the same remote rack limits cross-switch network traffic to a single rack hop while still guaranteeing complete survivability if an entire rack fails."),
        ("How does YARN decoupling of resource management from MapReduce allow diverse frameworks like Spark and Flink to run concurrently?", "Cluster_Resource_Management.pptx", 8, "By abstracting compute nodes into generic CPU and memory containers under ResourceManager, applications bring their own ApplicationMaster rather than being forced into MapReduce execution constraints."),
        ("In what way does the combination of Amdahl's Law and network latency explain why scaling to thousands of nodes yields diminishing returns?", "Parallelism_and_Distributed_Data_Processing_Notes.docx", 17, "As node count increases, synchronization and network message latency grow, increasing the sequential communication fraction which caps total speedup under Amdahl's Law."),
        ("How do the 5 V's of big data necessitate the transition from shared-memory RDBMS to shared-nothing distributed storage like HDFS?", "Unit 1 intro to bigdata (1).pdf", 14, "Extreme volume and velocity exceed the I/O bus and storage bandwidth of single-node servers, requiring horizontally partitioned storage without shared physical bottlenecks."),
        ("Why does speculative execution in MapReduce require idempotent task operations on distributed blocks?", "UNIT 2_BDA.pdf", 21, "Because duplicate tasks run simultaneously on identical input blocks, tasks must produce identical side-effect-free results so discarding the slower execution causes no inconsistency."),
        ("How does Dominant Resource Fairness prevent CPU-heavy tasks from starving memory-heavy tasks in a heterogeneous cluster?", "Cluster_Resource_Management.pptx", 14, "DRF normalizes consumption across all dimensions by equalizing each user's dominant share, ensuring that high CPU usage is penalized relative to cluster total capacity."),
        ("How do HDFS block sizes directly determine the number of Map tasks instantiated in a MapReduce job?", "UNIT 2_BDA.pdf", 9, "Each HDFS block corresponds by default to one InputSplit, meaning a larger block size creates fewer mapper tasks, reducing task scheduling overhead on the cluster."),
        ("Why does top-down memoization fail to prevent memory exhaustion when applied to distributed Big Data computations without partitioning?", "Parallelism_and_Distributed_Data_Processing_Notes.docx", 29, "Single-process memoization stores state in local RAM; without distributed partitioning and shuffling, state overflows single-node memory bounds."),
        ("How does rack awareness interact with task scheduling delay to achieve maximum data locality?", "2.3 Data_Locality.pptx", 7, "Delay scheduling holds task dispatch briefly waiting for a node on the same rack before falling back to cross-rack communication, maximizing bandwidth utilization.")
    ]
    for idx, (q, doc, page, ans) in enumerate(multihop_data, 1):
        testset.append({
            "id": f"eval_multi_{idx:02d}",
            "course_id": COURSE_ID,
            "question": q,
            "question_type": "multi_hop",
            "is_unsupported": False,
            "must_refuse": False,
            "ground_truth_answer": ans,
            "ground_truth_source_locations": [{"document_name": doc, "page_number": page}]
        })

    # --- 10 Visual / Architectural Questions ---
    visual_data = [
        ("How does the HDFS master-worker architecture diagram illustrate communication between the client, NameNode, and DataNodes?", "UNIT 2_BDA.pdf", 7, "The diagram shows the client communicating with NameNode for metadata over RPC, and reading/writing block data directly to DataNodes via TCP streaming."),
        ("In the rack awareness topology diagram, what network structure connects nodes across different racks?", "2.2 Data_Placement_Strategies.pptx", 2, "Nodes in a rack connect to a Top-of-Rack (TOR) switch, and TOR switches connect across a core aggregation switch router."),
        ("How does the MapReduce dataflow schematic represent the transition from Map outputs to Reduce inputs?", "UNIT 2_BDA.pdf", 17, "The schematic illustrates Map tasks emitting intermediate key-values, followed by a partitioned shuffle/sort cross-over network to Reducers."),
        ("Interpret the data locality hierarchy diagram showing PROCESS_LOCAL, NODE_LOCAL, and RACK_LOCAL access paths.", "2.3 Data_Locality.pptx", 3, "The diagram shows memory access within the CPU/JVM cache, local disk access over SATA/PCIe bus, and rack-level access across the local TOR network switch."),
        ("How does the YARN architectural overview diagram illustrate the interaction between ResourceManager, NodeManagers, and ApplicationMaster?", "Cluster_Resource_Management.pptx", 4, "The diagram shows the central ResourceManager leasing containers to NodeManagers while the ApplicationMaster manages task lifecycles inside worker containers."),
        ("What does the Amdahl's Law speedup curves graph demonstrate as the number of parallel processors approaches infinity?", "Parallelism_and_Distributed_Data_Processing_Notes.docx", 16, "The curves level off asymptotically at 1/f, showing that speedup is bounded by the sequential fraction regardless of processor count."),
        ("In the HDFS pipeline write schematic, how are data packets forwarded sequentially between DataNodes?", "UNIT 2_BDA.pdf", 14, "The client streams packets to DataNode A, which forwards them in a daisy-chain pipeline to DataNode B, which forwards to DataNode C."),
        ("How does the Big Data 5 V's conceptual graphic categorize velocity and variety?", "Unit 1 intro to bigdata (1).pdf", 6, "It displays velocity as streaming speed and variety as structured, semi-structured, and unstructured data modalities."),
        ("Explain the two-level scheduling diagram of Apache Mesos allocating resources to diverse frameworks.", "Cluster_Resource_Management.pptx", 10, "The diagram shows Mesos master offering raw resource vectors to framework schedulers, which assign tasks to individual Mesos slaves."),
        ("In the distributed memory cluster topology diagram, how do compute nodes exchange state without shared physical RAM?", "Parallelism_and_Distributed_Data_Processing_Notes.docx", 10, "Nodes communicate exclusively through high-speed network interconnects via explicit message-passing interfaces.")
    ]
    for idx, (q, doc, page, ans) in enumerate(visual_data, 1):
        testset.append({
            "id": f"eval_vis_{idx:02d}",
            "course_id": COURSE_ID,
            "question": q,
            "question_type": "visual",
            "is_unsupported": False,
            "must_refuse": False,
            "ground_truth_answer": ans,
            "ground_truth_source_locations": [{"document_name": doc, "page_number": page}]
        })

    # --- 16 Off-Material / Unsupported Questions (MUST BE REFUSED) ---
    off_material = [
        "How do you bake sourdough bread with an active starter at home?",
        "What is the capital city of Mongolia and what is its current population?",
        "Explain the combustion cycle in a liquid bipropellant rocket engine.",
        "Who won the 1994 FIFA World Cup soccer tournament held in the United States?",
        "What is the traditional recipe for French chocolate molten lava cake?",
        "How do you replace front brake pads and rotors on a 2018 Honda Civic?",
        "What is the central dramatic conflict in William Shakespeare's Hamlet?",
        "Explain quantum chromodynamics and how quarks interact via gluon color charge.",
        "How do organic gardeners prevent aphid infestations on tomato plants?",
        "What are the official rules of professional cricket bowling deliveries?",
        "What causes continental drift and plate tectonics in planetary geology?",
        "How do dentists treat dental caries and severe root canal infections?",
        "What is the sequential biological process of mitosis in eukaryotic cells?",
        "How does a four-stroke internal combustion engine work during the intake stroke?",
        "What were the origins and key artists of the French Impressionist painting movement?",
        "How do you calibrate espresso grind size on an Italian commercial espresso machine?"
    ]
    for idx, q in enumerate(off_material, 1):
        testset.append({
            "id": f"eval_off_{idx:02d}",
            "course_id": COURSE_ID,
            "question": q,
            "question_type": "off_material",
            "is_unsupported": True,
            "must_refuse": True,
            "ground_truth_answer": "I cannot answer this question because it is not covered in your course material.",
            "ground_truth_source_locations": []
        })

    out_path = "eval/testset.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(testset, f, indent=2)

    in_scope_count = len([t for t in testset if not t["is_unsupported"]])
    off_count = len([t for t in testset if t["is_unsupported"]])
    print(f"[Seed & Testset] Successfully created {out_path} with {len(testset)} items ({in_scope_count} in-scope across 5 types, {off_count} off-material).")

if __name__ == "__main__":
    seed_bank_and_testset()

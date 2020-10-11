# kafka-tr-issue-201011
Reproduction demo of a Kafka transactional producer issue that affects performance.

# Summary
For some reason the `send_offsets_to_transaction()` call will be 50+ times slower when there is more than one
message in the input topic of the transactor.

# The demo
The demo consists of two parts:
* a slightly modified copy of the example called `eos-transactions.py`
  * prints are replaced with sys.stdout writes to keep in sync with log output
  * each and every processed message is transacted one-by-one
  * transactor will wait for input and not exit
* a script called `demo.py` that:
  * produces input for the transactor
  * launches the transactor process (eos-transactions.py)
  * summarizes the logs and times it took for the processing to be done

The demo script has two modes of operation:
* parallel mode: input messages are produced in bulk
* serial mode: input messages are produced strictly after the reply message of the previous is received

# The problem
In parallel mode the `send_offsets_to_transaction()` is so much slower that it makes the serial mode finish faster in
comparison. This should not be the case intuitively since in serial processing the round-trip times are greater.

# Environment
The demo was tested with the following software:
* Linux 5.8.14
* Kafka 2.5.0, 2.6.0 (from docker-hub of bitnami/kafka)
* Python 3.8.6
* confluent-kafka 1.5.0

# Running the demo
1. Clone the repository and setup a python environment with the tools of your choice. The dependencies can be installed
from the `requirements.txt`.
2. Prepare a Kafka broker for testing with two topics for testing, which all have a single partition. 
The demo uses a static default string for the group_id so the topics can be re-used and only the new messages will be processed by every consumer.

### Serial demo example
```
$ /home/joe/PycharmProjects/.venv/kafka-tr-issue-201011/bin/python /home/joe/PycharmProjects/kafka-tr-issue-201011/demo.py -b 172.31.31.3:9092 -t demoinput1602409428 -o demooutput1602409428 -s
Running in SERIAL mode
The input producer will wait for the reply of the transactor before producing the next message.
Processing took 0.30998730659484863

Send offset times: [0.04938220977783203, 0.005151987075805664, 0.0031898021697998047, 0.002920866012573242, 0.002249002456665039, 0.002113819122314453, 0.00174713134765625, 0.0025207996368408203, 0.002359628677368164, 0.0022499561309814453, 0.002370119094848633, 0.0021266937255859375, 0.002241373062133789, 0.0024209022521972656, 0.002430438995361328, 0.002146005630493164, 0.0020325183868408203, 0.002163410186767578, 0.0022263526916503906, 0.0023109912872314453]
Send offset times average: 0.004817700386047364

Relevant log snippet from the middle:
:DEMO:START 1602409450.3086362
%7|1602409450.308|CGRPOP|rdkafka#consumer-1| [thrd:main]: Group "eos_example_cd817a22-b31d-4a2c-9e70-b905c126387b" received op GET_ASSIGNMENT (v0) in state up (join state started, v5 vs 0)
%7|1602409450.308|TXNAPI|rdkafka#producer-2| [thrd:app]: Transactional API called: send_offsets_to_transaction
%7|1602409450.308|SEND|rdkafka#producer-2| [thrd:TxnCoordinator]: TxnCoordinator/1001: Sent AddOffsetsToTxnRequest (v0, 102 bytes @ 0, CorrId 34)
%7|1602409450.309|ADDPARTS|rdkafka#producer-2| [thrd:main]: TxnCoordinator/1001: Adding partitions to transaction
%7|1602409450.309|SEND|rdkafka#producer-2| [thrd:TxnCoordinator]: TxnCoordinator/1001: Sent AddPartitionsToTxnRequest (v0, 92 bytes @ 0, CorrId 35)
%7|1602409450.309|RECV|rdkafka#producer-2| [thrd:TxnCoordinator]: TxnCoordinator/1001: Received AddOffsetsToTxnResponse (v0, 6 bytes, CorrId 34, rtt 0.92ms)
%7|1602409450.309|SEND|rdkafka#producer-2| [thrd:172.31.31.3:9092/bootstrap]: 172.31.31.3:9092/1001: Sent TxnOffsetCommitRequest (v0, 152 bytes @ 0, CorrId 28)
%7|1602409450.310|RECV|rdkafka#producer-2| [thrd:TxnCoordinator]: TxnCoordinator/1001: Received AddPartitionsToTxnResponse (v0, 46 bytes, CorrId 35, rtt 1.22ms)
%7|1602409450.310|ADDPARTS|rdkafka#producer-2| [thrd:main]: demooutput1602409428 [0] registered with transaction
%7|1602409450.310|WAKEUP|rdkafka#producer-2| [thrd:main]: 172.31.31.3:9092/1001: Wake-up
%7|1602409450.310|WAKEUP|rdkafka#producer-2| [thrd:main]: TxnCoordinator/1001: Wake-up
%7|1602409450.310|TOPPAR|rdkafka#producer-2| [thrd:172.31.31.3:9092/bootstrap]: 172.31.31.3:9092/1001: demooutput1602409428 [0] 1 message(s) in xmit queue (1 added from partition queue)
%7|1602409450.310|RECV|rdkafka#producer-2| [thrd:172.31.31.3:9092/bootstrap]: 172.31.31.3:9092/1001: Received TxnOffsetCommitResponse (v0, 46 bytes, CorrId 28, rtt 1.24ms)
%7|1602409450.310|TOPPAR|rdkafka#producer-2| [thrd:172.31.31.3:9092/bootstrap]: 172.31.31.3:9092/1001: demooutput1602409428 [0] 1 message(s) in xmit queue (0 added from partition queue)
:DEMO:END   1602409450.3110063 0.002370119094848633

Full output of the transactor:
%7|1602409447.121|MEMBERID|rdkafka#consumer-1| [thrd:app]: Group "eos_example_cd817a22-b31d-4a2c-9e70-b905c126387b": updating member id "(not-set)" -> ""
%7|1602409447.121|WAKEUPFD|rdkafka#consumer-1| [thrd:app]: GroupCoordinator: Enabled low-latency ops queue wake-ups
%7|1602409447.121|BROKER|rdkafka#consumer-1| [thrd:app]: GroupCoordinator: Added new broker with NodeId -1
%7|1602409447.121|BRKMAIN|rdkafka#consumer-1| [thrd:GroupCoordinator]: GroupCoordinator: Enter main broker thread
%7|1602409447.121|WAKEUPFD|rdkafka#consumer-1| [thrd:app]: 172.31.31.3:9092/bootstrap: Enabled low-latency ops queue wake-ups
%7|1602409447.121|BRKMAIN|rdkafka#consumer-1| [thrd::0/internal]: :0/internal: Enter main broker thread
...
```

### Parallel demo example
```
$ /home/joe/PycharmProjects/.venv/kafka-tr-issue-201011/bin/python /home/joe/PycharmProjects/kafka-tr-issue-201011/demo.py -b 172.31.31.3:9092 -t demoinput1602410701 -o demooutput1602410701
Running in PARALLEL mode
The input producer will produce all messages in parallel (at once) after the first message.
Processing took 1.9110004901885986

Send offset times: [0.049684762954711914, 0.004431247711181641, 0.1045372486114502, 0.10331964492797852, 0.1041402816772461, 0.10495209693908691, 0.10389399528503418, 0.10295701026916504, 0.10307526588439941, 0.10339474678039551, 0.1034994125366211, 0.10283136367797852, 0.10272407531738281, 0.10245895385742188, 0.10555815696716309, 0.10403847694396973, 0.10850381851196289, 0.10323119163513184, 0.10339903831481934, 0.10307693481445312]
Send offset times average: 0.09618538618087769

Relevant log snippet from the middle:
:DEMO:START 1602410740.6066911
%7|1602410740.606|CGRPOP|rdkafka#consumer-1| [thrd:main]: Group "eos_example_267be98e-3541-4b89-884b-848453b86a64" received op GET_ASSIGNMENT (v0) in state up (join state started, v5 vs 0)
%7|1602410740.606|TXNAPI|rdkafka#producer-2| [thrd:app]: Transactional API called: send_offsets_to_transaction
%7|1602410740.606|SEND|rdkafka#producer-2| [thrd:TxnCoordinator]: TxnCoordinator/1001: Sent AddOffsetsToTxnRequest (v0, 102 bytes @ 0, CorrId 50)
%7|1602410740.607|RECV|rdkafka#producer-2| [thrd:TxnCoordinator]: TxnCoordinator/1001: Received AddOffsetsToTxnResponse (v0, 6 bytes, CorrId 50, rtt 0.32ms)
%7|1602410740.607|RETRY|rdkafka#producer-2| [thrd:TxnCoordinator]: TxnCoordinator/1001: Retrying AddOffsetsToTxnRequest (v0, 102 bytes, retry 1/3, prev CorrId 50) in 100ms
%7|1602410740.607|ADDPARTS|rdkafka#producer-2| [thrd:main]: TxnCoordinator/1001: Adding partitions to transaction
%7|1602410740.607|SEND|rdkafka#producer-2| [thrd:TxnCoordinator]: TxnCoordinator/1001: Sent AddPartitionsToTxnRequest (v0, 92 bytes @ 0, CorrId 51)
%7|1602410740.608|RECV|rdkafka#producer-2| [thrd:TxnCoordinator]: TxnCoordinator/1001: Received AddPartitionsToTxnResponse (v0, 46 bytes, CorrId 51, rtt 0.42ms)
%7|1602410740.608|ADDPARTS|rdkafka#producer-2| [thrd:main]: TxnCoordinator/1001: AddPartitionsToTxn response: partition "demooutput1602410701": [0]: Broker: Producer attempted to update a transaction while another concurrent operation on the same transaction was ongoing
%7|1602410740.628|ADDPARTS|rdkafka#producer-2| [thrd:main]: TxnCoordinator/1001: Adding partitions to transaction
%7|1602410740.628|SEND|rdkafka#producer-2| [thrd:TxnCoordinator]: TxnCoordinator/1001: Sent AddPartitionsToTxnRequest (v0, 92 bytes @ 0, CorrId 52)
%7|1602410740.629|RECV|rdkafka#producer-2| [thrd:TxnCoordinator]: TxnCoordinator/1001: Received AddPartitionsToTxnResponse (v0, 46 bytes, CorrId 52, rtt 1.13ms)
%7|1602410740.629|ADDPARTS|rdkafka#producer-2| [thrd:main]: demooutput1602410701 [0] registered with transaction
%7|1602410740.629|TOPPAR|rdkafka#producer-2| [thrd:172.31.31.3:9092/bootstrap]: 172.31.31.3:9092/1001: demooutput1602410701 [0] 1 message(s) in xmit queue (1 added from partition queue)
%7|1602410740.629|PRODUCE|rdkafka#producer-2| [thrd:172.31.31.3:9092/bootstrap]: 172.31.31.3:9092/1001: demooutput1602410701 [0]: Produce MessageSet with 1 message(s) (76 bytes, ApiVersion 7, MsgVersion 2, MsgId 11, BaseSeq 10, PID{Id:0,Epoch:0}, uncompressed)
%7|1602410740.629|SEND|rdkafka#producer-2| [thrd:172.31.31.3:9092/bootstrap]: 172.31.31.3:9092/1001: Sent ProduceRequest (v7, 168 bytes @ 0, CorrId 28)
%7|1602410740.629|WAKEUP|rdkafka#producer-2| [thrd:main]: 172.31.31.3:9092/1001: Wake-up
%7|1602410740.629|WAKEUP|rdkafka#producer-2| [thrd:main]: TxnCoordinator/1001: Wake-up
%7|1602410740.630|RECV|rdkafka#producer-2| [thrd:172.31.31.3:9092/bootstrap]: 172.31.31.3:9092/1001: Received ProduceResponse (v7, 70 bytes, CorrId 28, rtt 0.94ms)
%7|1602410740.630|MSGSET|rdkafka#producer-2| [thrd:172.31.31.3:9092/bootstrap]: 172.31.31.3:9092/1001: demooutput1602410701 [0]: MessageSet with 1 message(s) (MsgId 11, BaseSeq 10) delivered
%7|1602410740.707|RETRY|rdkafka#producer-2| [thrd:TxnCoordinator]: TxnCoordinator/1001: Moved 1 retry buffer(s) to output queue
%7|1602410740.707|SEND|rdkafka#producer-2| [thrd:TxnCoordinator]: TxnCoordinator/1001: Sent AddOffsetsToTxnRequest (v0, 102 bytes @ 0, CorrId 53)
%7|1602410740.708|RECV|rdkafka#producer-2| [thrd:TxnCoordinator]: TxnCoordinator/1001: Received AddOffsetsToTxnResponse (v0, 6 bytes, CorrId 53, rtt 1.20ms)
%7|1602410740.708|SEND|rdkafka#producer-2| [thrd:172.31.31.3:9092/bootstrap]: 172.31.31.3:9092/1001: Sent TxnOffsetCommitRequest (v0, 152 bytes @ 0, CorrId 29)
%7|1602410740.710|RECV|rdkafka#producer-2| [thrd:172.31.31.3:9092/bootstrap]: 172.31.31.3:9092/1001: Received TxnOffsetCommitResponse (v0, 46 bytes, CorrId 29, rtt 1.30ms)
:DEMO:END   1602410740.7101905 0.1034994125366211

Full output of the transactor:
%7|1602410736.719|MEMBERID|rdkafka#consumer-1| [thrd:app]: Group "eos_example_267be98e-3541-4b89-884b-848453b86a64": updating member id "(not-set)" -> ""
%7|1602410736.719|WAKEUPFD|rdkafka#consumer-1| [thrd:app]: GroupCoordinator: Enabled low-latency ops queue wake-ups
%7|1602410736.719|BROKER|rdkafka#consumer-1| [thrd:app]: GroupCoordinator: Added new broker with NodeId -1
%7|1602410736.719|BRKMAIN|rdkafka#consumer-1| [thrd:GroupCoordinator]: GroupCoordinator: Enter main broker thread
%7|1602410736.719|WAKEUPFD|rdkafka#consumer-1| [thrd:app]: 172.31.31.3:9092/bootstrap: Enabled low-latency ops queue wake-ups
%7|1602410736.719|BROKER|rdkafka#consumer-1| [thrd:app]: 172.31.31.3:9092/bootstrap: Added new broker with NodeId -1
%7|1602410736.719|INIT|rdkafka#consumer-1| [thrd:app]: librdkafka v1.5.0 (0x10500ff) rdkafka#consumer-1 initialized (builtin.features gzip,snappy,ssl,sasl,regex,lz4,sasl_plain,sasl_scram,plugins,zstd,sasl_oauthbearer, STATIC_LINKING GCC GXX PKGCONFIG INSTALL GNULD LDS LIBDL PLUGINS STATIC_LIB_zlib ZLIB STATIC_LIB_libcrypto STATIC_LIB_libssl SSL STATIC_LIB_libzstd ZSTD HDRHISTOGRAM SYSLOG SNAPPY SOCKEM SASL_SCRAM SASL_OAUTHBEARER CRC32C_HW, debug 0xfffff)
%7|1602410736.719|BRKMAIN|rdkafka#consumer-1| [thrd::0/internal]: :0/internal: Enter main broker thread
...
```

### The logs
The main difference that the logs immediately show is that there is some "retry" operations when the times are bad:
```
...
%7|1602410740.607|RETRY|rdkafka#producer-2| [thrd:TxnCoordinator]: TxnCoordinator/1001: Retrying AddOffsetsToTxnRequest (v0, 102 bytes, retry 1/3, prev CorrId 50) in 100ms
...
%7|1602410740.707|RETRY|rdkafka#producer-2| [thrd:TxnCoordinator]: TxnCoordinator/1001: Moved 1 retry buffer(s) to output queue
...
```
However it is unclear to me what the cause of this is. There is one additional line that indicates a broker-side transaction error:
```
...
%7|1602410740.608|ADDPARTS|rdkafka#producer-2| [thrd:main]: TxnCoordinator/1001: AddPartitionsToTxn response: partition "demooutput1602410701": [0]: Broker: Producer attempted to update a transaction while another concurrent operation on the same transaction was ongoing
...
```
That I do not know how to correct either.

# Conclusion
It is unclear to me if this is a bug in librdkafka or the python binding, because there seems to be some failure on the broker side. (that could be the cause of some unintended behaviour by the transacting producer)

It is clear as day that the parallel processing **should** be faster than a serial one, but as the demo showcases it being 6 times slower.

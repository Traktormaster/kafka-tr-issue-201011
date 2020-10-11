import argparse
import os
import subprocess
import sys
import tempfile
import time
import uuid
from collections import defaultdict

from confluent_kafka.cimpl import Consumer, Producer

HERE = os.path.dirname(os.path.abspath(__file__))


def main(args):
    serial = args.serial
    num_messages = args.num_messages
    brokers = args.brokers
    group_id = args.group_id
    input_topic = args.input_topic
    input_partition = args.input_partition
    output_topic = args.output_topic

    if serial:
        print("Running in SERIAL mode")
        print("The input producer will wait for the reply of the transactor before producing the next message.")
    else:
        print("Running in PARALLEL mode")
        print("The input producer will produce all messages in parallel (at once) after the first message.")

    tr_args = [
        sys.executable, os.path.join(HERE, "eos-transactions.py"), "-b", brokers, "-g", group_id, "-t", input_topic,
        "-p", str(input_partition), "-o", output_topic,
    ]

    output_consumer = Consumer(
        {
            "bootstrap.servers": brokers,
            "group.id": str(uuid.uuid4()),
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "enable.partition.eof": False,
        }
    )
    output_consumer.subscribe([output_topic])

    input_producer = Producer({
        'bootstrap.servers': brokers,
    })

    with tempfile.NamedTemporaryFile(mode='w+') as f:
        tr_proc = subprocess.Popen(tr_args, stderr=subprocess.STDOUT, stdout=f, cwd=HERE, close_fds=True)
        try:
            time.sleep(1)
            assert tr_proc.poll() is None
            tx = 0
            for i in range(num_messages):
                input_producer.produce(input_topic, key=b"xy", value=str(tx).encode("ascii"))
                tx += 1
                assert input_producer.flush(10) == 0
                while serial or tx <= 1:
                    msg = output_consumer.poll(1.0)
                    if msg is None:
                        continue
                    assert msg.error() is None
                    if tx == 1:
                        t_start = time.time()
                    break
            if not serial:
                for _ in range(num_messages-1):
                    msg = output_consumer.poll(1.0)
                    if msg is None:
                        continue
                    assert msg.error() is None

            print("Processing took {}".format(time.time() - t_start))
        finally:
            if tr_proc.poll() is None:
                tr_proc.terminate()
                tr_proc.wait()
        f.seek(0)
        eos_out = f.read()

    i = 0
    c = False
    send_offset_logs = defaultdict(list)
    send_offset_times = []
    for line in eos_out.split("\n"):
        if line.startswith(":DEMO:START "):
            c = True
        if c:
            send_offset_logs[i].append(line)
        if line.startswith(":DEMO:END "):
            send_offset_times.append(float(line.rpartition(" ")[-1]))
            c = False
            i += 1

    print("\nSend offset times:", send_offset_times)
    print("Send offset times average:", sum(send_offset_times)/len(send_offset_times))

    print("\nRelevant log snippet from the middle:")
    print("\n".join(send_offset_logs[int(i/2)]))

    print("\nFull output of the transactor:")
    print(eos_out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Transactional performance impacting issue demo")
    parser.add_argument('-s', dest="serial", action="store_true",
                        help="Turn on strictly serial processing to showcase the performance " +
                        "when the issue is not present.")
    parser.add_argument('-n', dest="num_messages", default=20, type=int,
                        help="Number of messages to produce during the test")
    parser.add_argument('-b', dest="brokers", required=True,
                        help="Bootstrap broker(s) (host[:port])")
    parser.add_argument('-t', dest="input_topic", required=True,
                        help="Input topic to consume from, an external " +
                        "producer needs to produce messages to this topic")
    parser.add_argument('-o', dest="output_topic", default="output_topic",
                        help="Output topic")
    parser.add_argument('-p', dest="input_partition", default=0, type=int,
                        help="Input partition to consume from")
    parser.add_argument('-g', dest="group_id",
                        default="eos_example_" + str(uuid.uuid4()),
                        help="Consumer group")

    main(parser.parse_args())

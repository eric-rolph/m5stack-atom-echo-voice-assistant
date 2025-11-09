import os
stats = os.statvfs('/')
block_size = stats[0]
total_blocks = stats[2]
free_blocks = stats[3]
total_kb = (total_blocks * block_size) / 1024
used_kb = ((total_blocks - free_blocks) * block_size) / 1024
free_kb = (free_blocks * block_size) / 1024
print(f"Flash Total: {total_kb:.1f} KB")
print(f"Flash Used: {used_kb:.1f} KB")
print(f"Flash Free: {free_kb:.1f} KB")
print(f"Usage: {(used_kb/total_kb)*100:.1f}%")

import gc
gc.collect()
print(f"Free RAM: {gc.mem_free()} bytes ({gc.mem_free()/1024:.1f} KB)")
print(f"Used RAM: {gc.mem_alloc()} bytes ({gc.mem_alloc()/1024:.1f} KB)")
print(f"Total: {(gc.mem_free() + gc.mem_alloc())/1024:.1f} KB")

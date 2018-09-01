
def bulleted_list(items, bullet="-", space=1):
    spc = ' ' * space
    return "\n".join(u"%s%s%s" % (bullet, spc, x) for x in items)

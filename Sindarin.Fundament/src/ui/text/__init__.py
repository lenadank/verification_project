


def indent_block(text_block, indentation="    "):
    if isinstance(indentation, int): indentation = " "*indentation
    return "\n".join(indentation + line for line in text_block.splitlines())


def flush_left(text_block):
    return "\n".join(line.strip() for line in text_block.splitlines())

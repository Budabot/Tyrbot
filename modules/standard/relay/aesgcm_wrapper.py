import os

from cryptography.hazmat.primitives.ciphers import algorithms, Cipher, modes


class AESGCMWrapper:
    def __init__(self, key, nonce_length, tag_length=16):
        self.key = key
        self.nonce_length = nonce_length
        self.tag_length = tag_length

    def encrypt(self, plain_text):
        # Generate a random 96-bit IV.
        iv = os.urandom(self.nonce_length)

        # Construct an AES-GCM Cipher object with the given key and a
        # randomly generated IV.
        encryptor = Cipher(algorithms.AES(self.key), modes.GCM(iv)).encryptor()

        # Encrypt the plaintext and get the associated ciphertext.
        # GCM does not require padding.
        ciphertext = encryptor.update(plain_text) + encryptor.finalize()

        return iv + encryptor.tag + ciphertext

    def decrypt(self, encrypted_text):
        # Construct a Cipher object, with the key, iv, and additionally the
        # GCM tag used for authenticating the message.
        iv = encrypted_text[:self.nonce_length]
        rest = encrypted_text[self.nonce_length:]
        tag = rest[:self.tag_length:]
        rest = rest[self.tag_length:]

        decryptor = Cipher(algorithms.AES(self.key), modes.GCM(iv, tag)).decryptor()

        # Decryption gets us the authenticated plaintext.
        # If the tag does not match an InvalidTag exception will be raised.
        return decryptor.update(rest) + decryptor.finalize()

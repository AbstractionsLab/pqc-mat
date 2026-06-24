#ifndef OPENSSL_AES_H
#define OPENSSL_AES_H

#ifdef __cplusplus
extern "C" {
#endif

#define AES_BLOCK_SIZE 16

typedef struct aes_key_st {
    unsigned int rd_key[4 * (14 + 1)];
    int rounds;
} AES_KEY;

int AES_set_encrypt_key(const unsigned char *userKey, int bits, AES_KEY *key);
int AES_set_decrypt_key(const unsigned char *userKey, int bits, AES_KEY *key);
void AES_encrypt(const unsigned char *in, unsigned char *out, const AES_KEY *key);
void AES_decrypt(const unsigned char *in, unsigned char *out, const AES_KEY *key);

#ifdef __cplusplus
}
#endif

#endif /* OPENSSL_AES_H */

#include <openssl/evp.h>
#include <openssl/aes.h>
#include <cstring>

void aes_example(const unsigned char* key) {
    AES_KEY enc;
    AES_set_encrypt_key(key, 128, &enc);  // AES-128
    unsigned char in[16] = {0};
    unsigned char out[16];
    AES_encrypt(in, out, &enc);
}

int evp_example() {
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    EVP_EncryptInit_ex(ctx, EVP_aes_256_cbc(), nullptr, nullptr, nullptr);  // AES-256-CBC
    EVP_CIPHER_CTX_free(ctx);
    return 0;
}
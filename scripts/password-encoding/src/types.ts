export type PasswordBlob = {
  salt: string;
  verifier: string;
  cryptedpassword: string;
};

export type PasswordBlobInput = {
  username: string;
  newPassword: string;
  srpSaltHex?: string;
  cryptSaltHex?: string;
};

export type SaltOverride = (quartets: number) => string | undefined;

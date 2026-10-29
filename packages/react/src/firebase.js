// Supply modular Firebase SDK functions from the application's pinned dependency.
export function firebasePhoneAdapter({auth, signInWithPhoneNumber, verifier}) {
  let confirmation = null;
  let generation = 0;
  return {
    async send(phone) {
      const current = ++generation; confirmation = null;
      const result = await signInWithPhoneNumber(auth, phone, verifier);
      if (current === generation) confirmation = result;
    },
    async confirm(code) {
      if (!confirmation) throw new Error("Request an OTP first");
      const current = generation;
      const result = await confirmation.confirm(code);
      if (current !== generation) throw new Error("Phone flow changed");
      const token = await result.user.getIdToken(true);
      if (current !== generation) throw new Error("Phone flow changed");
      confirmation = null;
      return token;
    },
    cancel() { ++generation; confirmation = null; },
  };
}

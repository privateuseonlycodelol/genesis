#!/usr/bin/env node
import fs from "node:fs";
import type { PasswordBlobInput } from "../types.js";
import { referencePasswordBlob } from "../referencePasswordBlob.js";

const input = JSON.parse(fs.readFileSync(0, "utf8")) as PasswordBlobInput;
const out = referencePasswordBlob(input);
process.stdout.write(JSON.stringify(out));

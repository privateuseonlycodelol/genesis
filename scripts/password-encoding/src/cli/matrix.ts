#!/usr/bin/env node
import { runEncodingMatrix } from "../encodingMatrix.js";

const result = runEncodingMatrix();
console.log(JSON.stringify(result, null, 2));

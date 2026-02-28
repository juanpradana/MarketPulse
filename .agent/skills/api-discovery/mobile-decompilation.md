# Mobile App Analysis (Ethical Only)

## Android (APK)

### Tools Required
- apktool: `brew install apktool`
- jadx: `brew install jadx`
- dex2jar (optional)

### Process
1. **Extract APK**:
   ```bash
   apktool d app.apk -o app_decompiled
   ```

2. **Decompile to Java**:
   ```bash
   jadx app.apk -d app_java
   ```

3. **Search for endpoints**:
   ```bash
   grep -r "https://" app_java/ --include="*.java"
   grep -r "api\." app_java/ --include="*.java"
   ```

4. **Analyze resources**:
   - `res/values/strings.xml` - API keys, URLs
   - `AndroidManifest.xml` - Permissions, components
   - `assets/` - Configuration files

## iOS (IPA)

### Tools Required
- frida-ios-dump (for owned devices)
- class-dump or class-dump-z
- strings command

### Process
1. **Decrypt IPA** (on jailbroken device or owned app):
   ```bash
   frida-ios-dump -U com.example.app
   ```

2. **Extract strings**:
   ```bash
   strings Payload/App.app/App | grep -i "https\|api\|token"
   ```

3. **Analyze binary**:
   ```bash
   class-dump -H Payload/App.app/App -o headers/
   ```

## Security Considerations

- **ONLY** analyze apps you own or have permission to test
- **NEVER** distribute decompiled code
- **REPORT** vulnerabilities responsibly
- **COMPLY** with all applicable laws and terms of service
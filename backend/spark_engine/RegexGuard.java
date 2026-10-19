import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.regex.Pattern;

/** Separate process: the caller enforces a hard timeout and heap/stack limits. */
class RegexGuard {
    public static void main(String[] args) throws Exception {
        BufferedReader input = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        String text = new String(Base64.getDecoder().decode(input.readLine()), StandardCharsets.UTF_8);
        int group = Integer.parseInt(input.readLine());
        Pattern pattern = Pattern.compile(text);
        if (pattern.matcher("").find() || group < 0 || group > pattern.matcher("").groupCount()) {
            System.exit(2);
        }
        for (String probe : new String[]{"a".repeat(8192) + "!", " ".repeat(8192) + "!",
                "a@" + "a.".repeat(2048) + "!", "0".repeat(8192) + "!"}) {
            pattern.matcher(probe).find();
        }
        System.out.println("OK");
    }
}

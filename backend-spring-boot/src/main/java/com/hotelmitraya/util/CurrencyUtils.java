package com.hotelmitraya.util;

import java.math.BigDecimal;
import java.math.RoundingMode;

public class CurrencyUtils {

    private static final String[] ONES = {
        "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
        "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"
    };

    private static final String[] TENS = {
        "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"
    };

    public static String numberToWordsIndian(double amount) {
        BigDecimal bd = BigDecimal.valueOf(amount).setScale(2, RoundingMode.HALF_UP);
        long rupees = bd.longValue();
        int paise = bd.remainder(BigDecimal.ONE).multiply(BigDecimal.valueOf(100)).intValue();

        if (rupees == 0 && paise == 0) {
            return "Rupees Zero Only";
        }

        StringBuilder result = new StringBuilder("Rupees ");
        if (rupees > 0) {
            result.append(convertNumber(rupees));
        }

        if (paise > 0) {
            if (rupees > 0) {
                result.append(" and ");
            }
            result.append(convertNumber(paise)).append(" Paise");
        }

        result.append(" Only");
        return result.toString();
    }

    private static String convertNumber(long n) {
        if (n == 0) return "";

        StringBuilder sb = new StringBuilder();

        if (n >= 10000000) { // Crore
            sb.append(convertNumber(n / 10000000)).append(" Crore ");
            n %= 10000000;
        }

        if (n >= 100000) { // Lakh
            sb.append(convertNumber(n / 100000)).append(" Lakh ");
            n %= 100000;
        }

        if (n >= 1000) { // Thousand
            sb.append(convertNumber(n / 1000)).append(" Thousand ");
            n %= 1000;
        }

        if (n >= 100) { // Hundred
            sb.append(convertNumber(n / 100)).append(" Hundred ");
            n %= 100;
        }

        if (n > 0) {
            if (n < 20) {
                sb.append(ONES[(int) n]).append(" ");
            } else {
                sb.append(TENS[(int) (n / 10)]).append(" ");
                if (n % 10 > 0) {
                    sb.append(ONES[(int) (n % 10)]).append(" ");
                }
            }
        }

        return sb.toString().trim();
    }
}

import type { Resume } from "../api/resume";

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export function renderMonthYear(value: string): string {
  const match = /^(\d{4})-(\d{2})$/.exec(value);
  if (!match) {
    return value;
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  if (month < 1 || month > 12) {
    return value;
  }
  return `${MONTHS[month - 1]} ${year}`;
}

export function emptyResume(): Resume {
  return {
    id: null,
    schema_version: 1,
    personal_information: {
      full_name: "",
      headline: "",
      email: "",
      phone: "",
      location: "",
      website: "",
    },
    summary: "",
    skills: {},
    experience: [],
    education: [],
    projects: [],
    certifications: [],
  };
}
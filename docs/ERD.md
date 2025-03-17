dbdiagram.io 문법

```
// 사용자
Table User {
  id int [pk, increment]
  email varchar [unique, not null]
  password varchar [not null]
  username varchar [not null]
  first_name varchar
  last_name varchar
  phone_number varchar
  birth_date date
  gender varchar
  profile_image varchar
  is_admin boolean [default: false]
  created_at timestamp [default: `now()`]
  login_at timestamp
  logout_at timestamp
}

// 강사 프로필
Table InstructorProfile {
  id int [pk, increment]
  user_id int [ref: > User.id, not null, unique]
  bio text
  experience text
  qualification text
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

// 과정(나노 디그리)
Table Course {
  id int [pk, increment]
  title varchar [not null]
  description text
  thumbnail_image varchar
  short_description varchar
  difficulty_level varchar [note: "입문, 초급, 중급, 고급"]
  target_audience text
  estimated_time int [note: "예상 학습시간(시간)"]
  credit int [note: "학점"]
  price decimal [not null]
  instructor_id int [ref: > InstructorProfile.id, not null]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

// 과목
Table Subject {
  id int [pk, increment]
  course_id int [ref: > Course.id, not null]
  title varchar [not null]
  description text
  order_index int [not null]
  subject_type varchar [note: "일반, 중간고사, 기말고사"]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

// 강의
Table Lecture {
  id int [pk, increment]
  subject_id int [ref: > Subject.id, not null]
  title varchar [not null]
  description text
  order_index int [not null]
  lecture_type varchar [note: "동영상, 미션"]
  video_url varchar
  duration int [note: "동영상 길이(분)"]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

// 미션 문제(쪽지 시험)
Table MissionQuestion {
  id int [pk, increment]
  lecture_id int [ref: > Lecture.id, not null]
  question_text text [not null]
  option1 text [not null]
  option2 text [not null]
  option3 text [not null]
  option4 text [not null]
  option5 text [not null]
  correct_answer int [not null, note: "1~5 정답 번호"]
  order_index int [not null]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

// Q&A 질문
Table QnAQuestion {
  id int [pk, increment]
  user_id int [ref: > User.id, not null]
  lecture_id int [ref: > Lecture.id, not null]
  content text [not null]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

// Q&A 답변
Table QnAAnswer {
  id int [pk, increment]
  question_id int [ref: > QnAQuestion.id, not null]
  user_id int [ref: > User.id, not null]
  content text [not null]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

// 학습 진행 관련
Table Enrollment {
  id int [pk, increment]
  user_id int [ref: > User.id, not null]
  course_id int [ref: > Course.id, not null]
  status varchar [note: "enrolled, completed, certified"]
  progress_percentage int [default: 0, note: "과정 전체 진행률(%)"]
  certificate_number varchar
  certificate_issued_at timestamp
  enrolled_at timestamp [default: `now()`]
  last_activity_at timestamp
  completed_at timestamp

  indexes {
    (user_id, course_id) [unique]
  }
}

// 강의 진행 여부
Table LectureProgress {
  id int [pk, increment]
  user_id int [ref: > User.id, not null]
  lecture_id int [ref: > Lecture.id, not null]
  is_completed boolean [default: false, note: "강의를 완료했는지 여부"]
  completed_at timestamp
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]

  indexes {
    (user_id, lecture_id) [unique]
  }
}

// 미션(쪽지 시험 성적 및 결과)
Table MissionAttempt {
  id int [pk, increment]
  user_id int [ref: > User.id, not null]
  lecture_id int [ref: > Lecture.id, not null]
  score int
  is_passed boolean [default: false]
  user_answers json [note: "JSON 형식으로 저장된 사용자 답변"]
  started_at timestamp [default: `now()`]
  completed_at timestamp

  indexes {
    (user_id, lecture_id)
  }
}

// 중간고사 및 기말고사 파일 제출
Table ProjectSubmission {
  id int [pk, increment]
  user_id int [ref: > User.id, not null]
  subject_id int [ref: > Subject.id, not null]
  project_file varchar [not null]
  is_passed boolean [default: false]
  feedback text
  submitted_at timestamp [default: `now()`]
  reviewed_at timestamp
  reviewed_by int [ref: > User.id]
}

// 결제 관련
Table Payment {
  id int [pk, increment]
  user_id int [ref: > User.id, not null]
  course_id int [ref: > Course.id, not null]
  amount decimal [not null]
  payment_method varchar
  payment_status varchar [note: "pending, completed, failed, refunded"]
  merchant_uid varchar [unique]
  imp_uid varchar [unique]
  refund_reason text
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

// 과정 리뷰
Table CourseReview {
  id int [pk, increment]
  user_id int [ref: > User.id, not null]
  course_id int [ref: > Course.id, not null]
  rating int [not null, note: "리뷰 평점 1-5"]
  content text
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]

  indexes {
    (user_id, course_id) [unique]
  }
}

// 장바구니
Table Cart {
  id int [pk, increment]
  user_id int [ref: > User.id, not null, unique]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

// 장바구니 아이템(과정)
Table CartItem {
  id int [pk, increment]
  cart_id int [ref: > Cart.id, not null]
  course_id int [ref: > Course.id, not null]
  created_at timestamp [default: `now()`]

  indexes {
    (cart_id, course_id) [unique]
  }
}

// 수료증
Table Certificate {
  id int [pk, increment]
  user_id int [ref: > User.id, not null]
  enrollment_id int [ref: > Enrollment.id, not null, unique]
  certificate_number varchar [unique]
  issued_at timestamp [default: `now()`]
  pdf_file varchar
}

// 일별 통계 정보
Table DailyStatistics {
  id int [pk, increment]
  date date [unique]
  new_users int [default: 0, note: "신규 가입자 수"]
  active_users int [default: 0, note: "활성 사용자 수"]
  new_enrollments int [default: 0, note: "신규 수강 신청 수"]
  completed_lectures int [default: 0, note: "완료된 강의 수"]
  certificates_issued int [default: 0, note: "발급된 수료증 수"]
  revenue decimal [default: 0, note: "일일 매출액"]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}
```

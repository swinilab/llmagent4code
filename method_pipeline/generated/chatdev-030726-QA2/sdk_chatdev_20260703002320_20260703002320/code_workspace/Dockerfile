FROM eclipse-temurin:17-jdk-alpine
VOLUME /tmp
COPY pom.xml ./
COPY src ./src
RUN ./mvnw -B package --no-transfer-progress
ARG JAR_FILE=target/oms-0.0.1-SNAPSHOT.jar
COPY ${JAR_FILE} app.jar
ENTRYPOINT ["java","-jar","/app.jar"]
